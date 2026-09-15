"""
schemas/session.py  –  Member B
Pydantic v2 request/response schemas for Committee Sessions and Scoring.

Key design decisions:
  • SessionCreate omits `committee_id` and `created_by` — both are derived
    from the logged-in admin's JWT, so the API is tamper-proof.
  • ScoringCreate captures the 4 dimensions from the baseline's scoring table
    (Sections 35-39): attendance, tasks, engagement, and bonus.
  • SessionDetailOut nests a list of ScoringOut items so the frontend can
    display the full scoring table in a single GET call.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Committee Sessions ───────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    """JSON body for POST /api/sessions."""
    title: str
    description: str
    date: datetime
    visibility: str         # "public" or "committee_specific"
    status: Optional[str] = "scheduled"


class SessionOut(BaseModel):
    """JSON returned for each session in list views."""
    id: int
    committee_id: int
    title: str
    description: str
    date: datetime
    visibility: str
    status: Optional[str] = None
    created_by: int

    class Config:
        from_attributes = True


# ── Session Scoring ──────────────────────────────────────────────────────────

class ScoringCreate(BaseModel):
    """Body sent by an admin/QC when scoring a member for one session."""
    user_id: int
    attendance_status: str   # on_time | late_under_15 | late_over_15 | absent_excused | absent_unexcused
    task_status: str         # on_time | late | not_submitted
    engagement_status: str   # engaged | not_engaged
    bonus_points: int = 0    # optional manually-added extra points


class ScoringOut(BaseModel):
    """One row of the scoring table, returned inside SessionDetailOut."""
    id: int
    session_id: int
    user_id: int
    attendance_status: str
    task_status: str
    engagement_status: str
    bonus_points: int
    recorded_by: int

    class Config:
        from_attributes = True


class SessionDetailOut(BaseModel):
    """
    Full session details + the complete scoring table.
    Returned by GET /api/sessions/{id} so the frontend can render
    the session overview and member scores in a single request.
    """
    id: int
    committee_id: int
    title: str
    description: str
    date: datetime
    visibility: str
    status: Optional[str] = None
    created_by: int
    scoring: List[ScoringOut] = []

    class Config:
        from_attributes = True
