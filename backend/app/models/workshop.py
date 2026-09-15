from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from app.database import Base


class Workshop(Base):
    __tablename__ = "workshops"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    image_url = Column(String)
    instructor = Column(String)
    created_by = Column(Integer, ForeignKey("users.id"))
    # Note: no `parts` relationship like Course has — Workshops don't follow a
    # fixed sequential path, they just have one or more independent Sessions.


class WorkshopSession(Base):
    __tablename__ = "workshop_sessions"

    id = Column(Integer, primary_key=True)
    workshop_id = Column(Integer, ForeignKey("workshops.id"))
    title = Column(String)
    description = Column(String)
    date = Column(DateTime)
    mode = Column(String)  # "online" or "offline"
    location_or_link = Column(String)
    materials_url = Column(String, nullable=True)


class WorkshopAttendance(Base):
    __tablename__ = "workshop_attendance"

    id = Column(Integer, primary_key=True)
    workshop_session_id = Column(Integer, ForeignKey("workshop_sessions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String)  # "present" or "absent"
    recorded_by = Column(Integer, ForeignKey("users.id"))