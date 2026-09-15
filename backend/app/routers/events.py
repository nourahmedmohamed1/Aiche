"""
routers/events.py  –  Member B
Endpoints for Events & Site Visits (Section 22 of the baseline).

Endpoints:
  GET  /api/events              — List all events (public, no auth)
  POST /api/events              — Create an event [Admin+]
  POST /api/events/{id}/register   — Register for an event [Student/Member]
  POST /api/events/{id}/attendance — Mark attendance + award points [Admin]

Design notes:
  • Event status (Upcoming / Closed / Finished) is COMPUTED at response time
    from `date` and `registration_deadline`, never stored — this prevents
    stale status values that would require a background cron job to update.
  • Registration is rejected once `registration_deadline` has passed,
    enforcing the baseline's auto-close rule.
"""

import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import EventSiteVisit, EventRegistration, EventAttendance
from app.models.user import User
from app.schemas.event import (
    EventCreate, EventOut, AttendanceCreate, EventAttendanceOut,
)
from app.dependencies import get_current_user, require_role
from app.core_logic import add_point_entry

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _compute_event_status(event: EventSiteVisit) -> str:
    """
    Derive the display status on-the-fly (Section 24 of the baseline).
    • Upcoming           — registration is still open AND event hasn't happened
    • Registration Closed — past the deadline but the event date hasn't arrived
    • Finished           — event date is in the past
    """
    now = datetime.datetime.utcnow()
    if now < event.registration_deadline:
        return "upcoming"
    elif now < event.date:
        return "registration_closed"
    else:
        return "finished"


# Maps attendance status → (points, reason) per Section 37 of the baseline.
ATTENDANCE_POINTS = {
    "attended":           (2,  "Event attended"),
    "absent_excused":     (0,  "Event absent (excused)"),
    "absent_unexcused":   (-1, "Event absent without excuse"),
}


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db)):
    """
    Public — no auth required.  Returns every event/site visit with a
    computed `status` field so the frontend can show labels without doing
    date arithmetic itself.
    """
    events = db.query(EventSiteVisit).all()
    result = []
    for ev in events:
        out = EventOut.model_validate(ev)
        out.status = _compute_event_status(ev)
        result.append(out)
    return result


@router.post("/", response_model=EventOut, status_code=201)
def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "committee_admin", "president", "vice_president", "secretary"
    )),
):
    """Create an event or site visit.  `created_by` is set from the JWT."""
    new_event = EventSiteVisit(
        type=event.type,
        title=event.title,
        description=event.description,
        date=event.date,
        location=event.location,
        registration_deadline=event.registration_deadline,
        created_by=current_user.id,
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # Build response with computed status.
    out = EventOut.model_validate(new_event)
    out.status = _compute_event_status(new_event)
    return out


@router.post("/{event_id}/register")
def register_for_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register the logged-in user for an event.
    Rejected if the registration deadline has already passed.
    """
    event = db.query(EventSiteVisit).filter(EventSiteVisit.id == event_id).first()
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")

    # Enforce the registration deadline.
    if datetime.datetime.utcnow() > event.registration_deadline:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Registration is closed")

    # Prevent duplicate registrations.
    existing = db.query(EventRegistration).filter_by(
        event_id=event_id, user_id=current_user.id
    ).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Already registered")

    registration = EventRegistration(
        event_id=event_id,
        user_id=current_user.id,
        registered_at=datetime.datetime.utcnow(),
    )
    db.add(registration)
    db.commit()
    return {"message": "Registered successfully"}


@router.post("/{event_id}/attendance")
def record_event_attendance(
    event_id: int,
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "committee_admin", "president", "vice_president", "secretary"
    )),
):
    """
    Admin marks a user Attended / Absent for an event.
    Automatically creates a point_entries row per Section 37's scoring table.
    """
    event = db.query(EventSiteVisit).filter(EventSiteVisit.id == event_id).first()
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")

    # Prevent duplicate attendance records.
    existing = db.query(EventAttendance).filter_by(
        event_id=event_id, user_id=data.user_id
    ).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Attendance already recorded")

    attendance = EventAttendance(
        event_id=event_id,
        user_id=data.user_id,
        status=data.status,
    )
    db.add(attendance)

    # Award/deduct points based on attendance status.
    points_info = ATTENDANCE_POINTS.get(data.status, (0, "Unknown status"))
    points_earned = points_info[0]
    add_point_entry(
        db,
        user_id=data.user_id,
        source_type="event",
        source_id=event_id,
        points=points_earned,
        reason=points_info[1],
    )

    db.commit()
    return {"message": "Attendance recorded", "points_earned": points_earned}
