from pydantic import BaseModel
from typing import Optional, List
from app.models.course import PartType


class CoursePartBase(BaseModel):
    title: str
    type: PartType
    order_index: int
    content_url: Optional[str] = None


class CoursePartCreate(CoursePartBase):
    pass


class CoursePartUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[PartType] = None
    order_index: Optional[int] = None
    content_url: Optional[str] = None


class CoursePartOut(CoursePartBase):
    id: int
    course_id: int

    class Config:
        from_attributes = True


class CourseBase(BaseModel):
    title: str
    description: Optional[str] = ""
    image_url: Optional[str] = None
    instructor: Optional[str] = "AIChE Instructor"
    level: Optional[str] = "Beginner"
    duration: Optional[str] = "Self-paced"


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    instructor: Optional[str] = None
    level: Optional[str] = None
    duration: Optional[str] = None


class CourseOut(CourseBase):
    id: int
    students: int = 0
    parts: List[CoursePartOut] = []

    class Config:
        from_attributes = True


CourseDetailOut = CourseOut


class CourseProgressUpdate(BaseModel):
    status: str


class CourseProgressOut(BaseModel):
    id: int
    user_id: int
    course_part_id: int
    status: str

    class Config:
        from_attributes = True


class CertificateCreate(BaseModel):
    type: str
    source_id: int


class CertificateOut(BaseModel):
    id: int
    user_id: int
    type: str
    source_id: int
    pdf_url: str

    class Config:
        from_attributes = True
