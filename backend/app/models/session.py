from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship
from app.database import Base

session_visibility_committees = Table(
    "session_visibility_committees", Base.metadata,
    Column("session_id", Integer, ForeignKey("committee_sessions.id")),
    Column("committee_id", Integer, ForeignKey("committees.id")),
)


class CommitteeSession(Base):
    __tablename__ = "committee_sessions"

    id = Column(Integer, primary_key=True)
    committee_id = Column(Integer, ForeignKey("committees.id"))
    title = Column(String)
    description = Column(String)
    date = Column(DateTime)
    visibility = Column(String)  # "public" or "committee_specific"
    status = Column(String)
    created_by = Column(Integer, ForeignKey("users.id"))

    committee = relationship("Committee")
    target_committees = relationship("Committee", secondary=session_visibility_committees)


class SessionScoring(Base):
    __tablename__ = "session_scoring"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("committee_sessions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    attendance_status = Column(String)
    task_status = Column(String)
    engagement_status = Column(String)
    bonus_points = Column(Integer, default=0)
    recorded_by = Column(Integer, ForeignKey("users.id"))