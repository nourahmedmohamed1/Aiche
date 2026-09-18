from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class WorkshopSessionBase(BaseModel):
    title: str
    description: Optional[str] = ""
    date: datetime
    mode: str = "online"  # "online" or "offline"
    location_or_link: str
    materials_url: Optional[str] = None


class WorkshopSessionCreate(WorkshopSessionBase):
    pass


class WorkshopSessionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[datetime] = None
    mode: Optional[str] = None
    location_or_link: Optional[str] = None
    materials_url: Optional[str] = None


class WorkshopSessionOut(WorkshopSessionBase):
    id: int
    workshop_id: int

    class Config:
        from_attributes = True


class WorkshopBase(BaseModel):
    title: str
    description: Optional[str] = ""
    image_url: Optional[str] = None
    instructor: Optional[str] = "AIChE Instructor"


class WorkshopCreate(WorkshopBase):
    pass


class WorkshopUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    instructor: Optional[str] = None


class WorkshopOut(WorkshopBase):
    id: int
    sessions_count: int = 0
    sessions: List[WorkshopSessionOut] = []

    class Config:
        from_attributes = True
