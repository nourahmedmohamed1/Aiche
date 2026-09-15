"""
routers/points.py  –  Member B
Endpoints for the Point System (Sections 35-41 of the baseline).

Endpoints:
  GET /api/points/{user_id}/total   — Live total (SUM over point_entries) [Member+]
  GET /api/points/{user_id}/history — Full point history, newest first [Member+]

Design notes:
  • Total Points is NEVER stored as an editable column — it's always a live
    SUM calculation over the point_entries table (Section 9.2 of the guide).
  • Point History returns every individual point_entries row so the frontend
    can show the granular breakdown (Section 41 of the baseline).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.point import PointEntry
from app.models.user import User
from app.schemas.point import PointEntryOut, TotalPointsOut
from app.dependencies import require_role
from app.core_logic import get_total_points

router = APIRouter()


@router.get("/{user_id}/total", response_model=TotalPointsOut)
def total_points(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "member", "committee_admin", "president", "vice_president", "secretary"
    )),
):
    """
    Live SUM over point_entries — see Section 9.2.
    The baseline explicitly says "Total Points is NOT entered manually."
    """
    return TotalPointsOut(
        user_id=user_id,
        total_points=get_total_points(db, user_id),
    )


@router.get("/{user_id}/history", response_model=list[PointEntryOut])
def point_history(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "member", "committee_admin", "president", "vice_president", "secretary"
    )),
):
    """
    Every individual point_entries row for this user, newest first.
    This is exactly the "Point History" list from Section 41.
    """
    return (
        db.query(PointEntry)
        .filter(PointEntry.user_id == user_id)
        .order_by(PointEntry.created_at.desc())
        .all()
    )
