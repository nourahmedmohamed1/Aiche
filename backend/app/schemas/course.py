"""
schemas/course.py
Pydantic v2 request/response schemas for Courses, Course Parts, Progress tracking, and Certificates.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.course import PartType, ProgressStatus


# ── Course Part Schemas ───────────────────────────────────────────────────────

class CoursePartBase(BaseModel):
    type: PartType
    order_index: int
    title: str
    content_url: Optional[str] = None


class CoursePartCreate(CoursePartBase):
    """Payload for creating a new part inside a course."""
    pass


class CoursePartUpdate(BaseModel):
    """Payload for updating a course part."""
    type: Optional[PartType] = None
    order_index: Optional[int] = None
    title: Optional[str] = None
    content_url: Optional[str] = None


class CoursePartOut(CoursePartBase):
    """Public representation of a course part."""
    id: int
    course_id: int

    class Config:
        from_attributes = True


# ── Course Schemas ────────────────────────────────────────────────────────────

class CourseBase(BaseModel):
    title: str
    description: str
    image_url: Optional[str] = None
    instructor: str
    level: str
    duration: str


class CourseCreate(CourseBase):
    """Payload for creating a new course."""
    pass


class CourseUpdate(BaseModel):
    """Payload for updating course details."""
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    instructor: Optional[str] = None
    level: Optional[str] = None
    duration: Optional[str] = None


class CourseOut(CourseBase):
    """Course overview returned in list endpoints."""
    id: int
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class CourseDetailOut(CourseOut):
    """Detailed course response including all parts in order."""
    parts: List[CoursePartOut] = []

    class Config:
        from_attributes = True


# ── Course Progress Schemas ───────────────────────────────────────────────────

class CourseProgressUpdate(BaseModel):
    """Payload for updating a user's progress on a course part."""
    status: ProgressStatus
    completion_type: Optional[str] = None


class CourseProgressOut(BaseModel):
    """Representation of a user's progress in a course part."""
    id: int
    user_id: int
    course_part_id: int
    status: ProgressStatus
    completion_type: Optional[str] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Certificate Schemas ───────────────────────────────────────────────────────

class CertificateCreate(BaseModel):
    """Payload for issuing a certificate."""
    user_id: int
    type: str
    source_id: int
    grade: Optional[float] = None
    pdf_url: str


class CertificateOut(BaseModel):
    """Representation of an issued certificate."""
    id: int
    user_id: int
    type: str
    source_id: int
    grade: Optional[float] = None
    pdf_url: str
    issued_at: datetime

    class Config:
        from_attributes = True
