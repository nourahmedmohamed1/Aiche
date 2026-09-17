"""
schemas/point.py  –  Member B
Pydantic v2 request/response schemas for Points, Committee Database,
Monthly Reports, Feedback, and Access Permissions.

These schemas cover all the "operations" features the baseline assigns
to Member B in the 2-member split (Section 15).
"""

from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


# ── Points ───────────────────────────────────────────────────────────────────

class PointEntryOut(BaseModel):
    """One row from the point_entries table — shown in Point History."""
    id: int
    user_id: int
    source_type: str        # "task" | "attendance" | "event" | "engagement" | "bonus"
    source_id: int
    points: int             # positive = earned, negative = deducted
    reason: str             # human-readable label, e.g. "Task submitted on time"
    created_at: datetime

    class Config:
        from_attributes = True


class TotalPointsOut(BaseModel):
    """Wrapper returned by GET /api/points/{user_id}/total."""
    user_id: int
    total_points: int


# ── Committee Database ───────────────────────────────────────────────────────

from pydantic import field_validator
from typing import Dict

class CommitteeDatabaseCreate(BaseModel):
    """Body for POST /api/committees/{id}/database — a flexible JSON row."""
    row_data: Dict[str, Any]  # dict with arbitrary keys

    @field_validator("row_data")
    def validate_row_data_is_dict(cls, v):
        if not isinstance(v, dict):
            raise ValueError("row_data must be a JSON object (dict)")
        return v


class CommitteeDatabaseUpdate(BaseModel):
    """Body for PUT /api/committees/{id}/database/{row_id} — updated flexible JSON row."""
    row_data: Dict[str, Any]

    @field_validator("row_data")
    def validate_row_data_is_dict(cls, v):
        if not isinstance(v, dict):
            raise ValueError("row_data must be a JSON object (dict)")
        return v


class CommitteeDatabaseOut(BaseModel):
    """One row returned from the committee's spreadsheet-style database."""
    id: int
    committee_id: int
    row_data: Any
    created_by: int
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Monthly Reports ──────────────────────────────────────────────────────────

class MonthlyReportCreate(BaseModel):
    """Body for POST /api/reports/members/{id}/monthly-report (uploaded by QC)."""
    file_url: str           # Cloudinary link to the uploaded report PDF
    month: str              # e.g. "2026-09"


class MonthlyReportOut(BaseModel):
    """Returned after a report is uploaded."""
    id: int
    member_id: int
    file_url: str
    month: str
    uploaded_by: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ── Feedback ─────────────────────────────────────────────────────────────────

class FeedbackCreate(BaseModel):
    """Body for POST /api/feedback."""
    target_type: str        # "course" | "workshop" | "event" | "site_visit"
    target_id: int          # id of the course/workshop/event/site_visit
    comment: str


class FeedbackOut(BaseModel):
    """Returned whenever feedback data is sent back to the client."""
    id: int
    user_id: int
    target_type: str
    target_id: int
    comment: str
    is_reported: bool
    is_deleted: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Access Permissions ───────────────────────────────────────────────────────

class AccessPermissionCreate(BaseModel):
    """Body for POST /api/access-permissions (President/VP/Secretary only)."""
    section_name: str       # e.g. "courses", "events"
    committee_id: int       # which committee gains/loses access
    can_edit: bool          # True = grant, False = revoke


class AccessPermissionOut(BaseModel):
    """Returned after creating/updating an access permission."""
    id: int
    section_name: str
    committee_id: int
    can_edit: bool
    granted_by: int
    updated_at: datetime

    class Config:
        from_attributes = True
