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


# ── UTC+3 Timezone Helpers ───────────────────────────────────────────────────

TZ_UTC3 = datetime.timezone(datetime.timedelta(hours=3))


def get_now_utc3() -> datetime.datetime:
    """Returns the current datetime in UTC+3 timezone."""
    return datetime.datetime.now(TZ_UTC3)


def _normalize_to_utc3(dt: datetime.datetime) -> datetime.datetime:
    """Ensures a datetime object is localized to UTC+3."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ_UTC3)
    return dt.astimezone(TZ_UTC3)


def _compute_event_status(event: EventSiteVisit) -> str:
    """
    Derive the display status on-the-fly in UTC+3:
    • upcoming             — now < registration_deadline
    • closed_registration  — registration_deadline <= now < date
    • finished             — now >= date
    """
    now = get_now_utc3()
    reg_deadline = _normalize_to_utc3(event.registration_deadline)
    event_date = _normalize_to_utc3(event.date)

    if now < reg_deadline:
        return "upcoming"
    elif now < event_date:
        return "closed_registration"
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
    Public — no auth required. Returns every event/site visit with a
    computed `status` field calculated in UTC+3.
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
    """Create an event or site visit. Datetimes are normalized to UTC+3."""
    date_utc3 = _normalize_to_utc3(event.date)
    deadline_utc3 = _normalize_to_utc3(event.registration_deadline)

    new_event = EventSiteVisit(
        type=event.type,
        title=event.title,
        description=event.description,
        date=date_utc3,
        location=event.location,
        registration_deadline=deadline_utc3,
        created_by=current_user.id,
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

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
    Rejected with 400 'Registration is closed' if registration_deadline has passed.
    """
    event = db.query(EventSiteVisit).filter(EventSiteVisit.id == event_id).first()
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")

    now = get_now_utc3()
    reg_deadline = _normalize_to_utc3(event.registration_deadline)

    # Enforce the registration deadline cutoff in UTC+3
    if now > reg_deadline:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Registration is closed")

    # Prevent duplicate registrations.
    existing = db.query(EventRegistration).filter_by(
        event_id=event_id, user_id=current_user.id
    ).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Already registered")

    registration = EventRegistration(
        event_id=event_id,
        user_id=current_user.id,
        registered_at=now,
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
