from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Workshop(Base):
    __tablename__ = "workshops"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    image_url = Column(String)
    instructor = Column(String)
    created_by = Column(Integer, ForeignKey("users.id"))

    sessions = relationship("WorkshopSession", back_populates="workshop", cascade="all, delete-orphan")


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

    workshop = relationship("Workshop", back_populates="sessions")
    attendances = relationship("WorkshopAttendance", back_populates="session", cascade="all, delete-orphan")


class WorkshopAttendance(Base):
    __tablename__ = "workshop_attendance"

    id = Column(Integer, primary_key=True)
    workshop_session_id = Column(Integer, ForeignKey("workshop_sessions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String)  # "present" or "absent"
    recorded_by = Column(Integer, ForeignKey("users.id"))

    session = relationship("WorkshopSession", back_populates="attendances")