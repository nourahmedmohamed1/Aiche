"""
schemas/event.py  – 
Pydantic v2 request/response schemas for Events & Site Visits.

Key design decisions:
  • EventCreate intentionally omits `created_by` — it's stamped server-side
    from the JWT, preventing clients from impersonating other admins.
  • EventOut includes a computed `status` field (Upcoming / Closed / Finished)
    that is calculated on-the-fly from `date` and `registration_deadline`,
    matching Section 24 of the baseline.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Events / Site Visits ─────────────────────────────────────────────────────

class EventCreate(BaseModel):
    """JSON body for POST /api/events — all fields an admin must supply."""
    type: str               # "event" or "site_visit"
    title: str
    description: str
    date: datetime           # when the event takes place
    location: str
    registration_deadline: datetime  # cutoff for sign-ups


class EventOut(BaseModel):
    """JSON returned whenever we send an event back to the client."""
    id: int
    type: str
    title: str
    description: str
    date: datetime
    location: str
    registration_deadline: datetime
    created_by: int
    status: Optional[str] = None   # computed at response-time by the router

    class Config:
        from_attributes = True
        # Lets Pydantic build this schema directly from a SQLAlchemy model.


# ── Event Registration ───────────────────────────────────────────────────────

class EventRegistrationOut(BaseModel):
    """Returned after a user successfully registers for an event."""
    id: int
    event_id: int
    user_id: int
    registered_at: datetime

    class Config:
        from_attributes = True


# ── Event Attendance ─────────────────────────────────────────────────────────

class AttendanceCreate(BaseModel):
    """Body sent by an admin when marking attendance (events, workshops, etc.)."""
    user_id: int
    status: str  # "attended" | "absent_excused" | "absent_unexcused"


class EventAttendanceOut(BaseModel):
    """Returned after attendance is recorded."""
    id: int
    event_id: int
    user_id: int
    status: str

    class Config:
        from_attributes = True
