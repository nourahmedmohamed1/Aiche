"""
routers/sessions.py  –  Member B
Endpoints for Committee Sessions and Scoring (Sections 30-39 of the baseline).

Endpoints:
  GET  /api/sessions              — List visible sessions [Member+]
  POST /api/sessions              — Create a session [Committee Admin+]
  GET  /api/sessions/{id}         — Session details + scoring table [Member+]
  POST /api/sessions/{id}/scoring — Save member scoring [Admin/QC]

Design notes:
  • Visibility filtering uses get_visible_sessions() from core_logic.py,
    which handles the QC special case and the "own committee + public" rule.
  • Scoring writes individual point_entries for each dimension (attendance,
    task, engagement, bonus) so the Point History (Section 41) shows
    granular line-items, not just a single lump sum.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.session import CommitteeSession, SessionScoring
from app.models.user import User
from app.schemas.session import (
    SessionCreate, SessionOut, ScoringCreate, ScoringOut, SessionDetailOut,
)
from app.dependencies import get_current_user, require_role
from app.core_logic import get_visible_sessions, add_point_entry

router = APIRouter()


# ── Scoring point maps (Sections 35-39 of the baseline) ─────────────────────

ATTENDANCE_POINTS = {
    "on_time":            (2,  "Session attendance: on time"),
    "late_under_15":      (1,  "Session attendance: late (under 15 min)"),
    "late_over_15":       (0,  "Session attendance: late (over 15 min)"),
    "absent_excused":     (0,  "Session attendance: absent (excused)"),
    "absent_unexcused":   (-1, "Session attendance: absent (unexcused)"),
}

TASK_POINTS = {
    "on_time":       (2,  "Task submitted on time"),
    "late":          (0,  "Task submitted after deadline"),
    "not_submitted": (-1, "Task not submitted"),
}

ENGAGEMENT_POINTS = {
    "engaged":       (1,  "Engaged during session"),
    "not_engaged":   (0,  "Not engaged during session"),
}


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[SessionOut])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "member", "committee_admin", "president", "vice_president", "secretary"
    )),
):
    """
    Returns only the sessions visible to the current user.
    Students are excluded — only Members and above can see sessions (Section 2.2).
    """
    return get_visible_sessions(db, current_user)


@router.post("/", response_model=SessionOut, status_code=201)
def create_session(
    session: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "committee_admin", "president", "vice_president", "secretary"
    )),
):
    """Create a committee session.  `committee_id` + `created_by` from JWT."""
    new_session = CommitteeSession(
        committee_id=current_user.committee_id,
        title=session.title,
        description=session.description,
        date=session.date,
        visibility=session.visibility,
        status=session.status,
        created_by=current_user.id,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


@router.get("/{session_id}", response_model=SessionDetailOut)
def get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "member", "committee_admin", "president", "vice_president", "secretary"
    )),
):
    """
    Session details + the full scoring table (all scored members).
    Returns a nested structure so the frontend can render both the session
    overview and the scoring grid in a single GET request.
    """
    session = db.query(CommitteeSession).filter(
        CommitteeSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    # Fetch all scoring rows for this session.
    scoring_rows = db.query(SessionScoring).filter(
        SessionScoring.session_id == session_id
    ).all()

    # Build nested response.
    return SessionDetailOut(
        id=session.id,
        committee_id=session.committee_id,
        title=session.title,
        description=session.description,
        date=session.date,
        visibility=session.visibility,
        status=session.status,
        created_by=session.created_by,
        scoring=[ScoringOut.model_validate(row) for row in scoring_rows],
    )


@router.post("/{session_id}/scoring")
def save_scoring(
    session_id: int,
    data: ScoringCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "committee_admin", "president", "vice_president", "secretary"
    )),
):
    """
    Save or update one member's attendance/task/engagement/bonus for a session.
    Each field maps to a specific point value and writes its own point_entries row.
    `source_id` points back to the `session_scoring` row.
    Re-scoring replaces previous entries in a single transaction without duplication.
    """
    from app.models.point import PointEntry

    session = db.query(CommitteeSession).filter(
        CommitteeSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    # Check for existing scoring row for this user x session
    existing = db.query(SessionScoring).filter_by(
        session_id=session_id, user_id=data.user_id
    ).first()

    if existing:
        # Delete previous point entries for this scoring row to avoid duplication
        db.query(PointEntry).filter(
            PointEntry.user_id == data.user_id,
            PointEntry.source_type.in_(["attendance", "task", "engagement", "bonus"]),
            (PointEntry.source_id == existing.id) | (PointEntry.source_id == session_id)
        ).delete(synchronize_session=False)

        # Update scoring row
        existing.attendance_status = data.attendance_status
        existing.task_status = data.task_status
        existing.engagement_status = data.engagement_status
        existing.bonus_points = data.bonus_points
        existing.recorded_by = current_user.id
        scoring = existing
    else:
        # Create new scoring row
        scoring = SessionScoring(
            session_id=session_id,
            user_id=data.user_id,
            attendance_status=data.attendance_status,
            task_status=data.task_status,
            engagement_status=data.engagement_status,
            bonus_points=data.bonus_points,
            recorded_by=current_user.id,
        )
        db.add(scoring)
        db.flush()  # Flush to populate scoring.id

    # ── Award points per dimension using scoring.id as source_id ──────────────
    total_points = 0

    # Attendance points
    att_info = ATTENDANCE_POINTS.get(data.attendance_status, (0, "Unknown attendance"))
    add_point_entry(db, data.user_id, "attendance", scoring.id, att_info[0], att_info[1])
    total_points += att_info[0]

    # Task points
    task_info = TASK_POINTS.get(data.task_status, (0, "Unknown task status"))
    add_point_entry(db, data.user_id, "task", scoring.id, task_info[0], task_info[1])
    total_points += task_info[0]

    # Engagement points
    eng_info = ENGAGEMENT_POINTS.get(data.engagement_status, (0, "Unknown engagement"))
    add_point_entry(db, data.user_id, "engagement", scoring.id, eng_info[0], eng_info[1])
    total_points += eng_info[0]

    # Bonus points (only if non-zero)
    if data.bonus_points:
        add_point_entry(
            db, data.user_id, "bonus", scoring.id,
            data.bonus_points, f"Bonus points ({data.bonus_points})"
        )
        total_points += data.bonus_points

    db.commit()
    return {"message": "Scoring saved", "points_added": total_points, "scoring_id": scoring.id}
