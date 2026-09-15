from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from app.database import Base


class EventSiteVisit(Base):
    __tablename__ = "events_site_visits"

    id = Column(Integer, primary_key=True)
    type = Column(String)  # "event" or "site_visit"
    title = Column(String)
    description = Column(String)
    date = Column(DateTime)
    location = Column(String)
    registration_deadline = Column(DateTime)
    created_by = Column(Integer, ForeignKey("users.id"))


class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events_site_visits.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    registered_at = Column(DateTime)


class EventAttendance(Base):
    __tablename__ = "event_attendance"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events_site_visits.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String)  # "attended" | "absent_excused" | "absent_unexcused"