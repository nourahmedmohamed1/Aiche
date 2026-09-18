from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, JSON
from app.database import Base
import datetime


class PointEntry(Base):
    __tablename__ = "point_entries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    source_type = Column(String)
    source_id = Column(Integer)
    points = Column(Integer)
    reason = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CommitteeDatabaseRow(Base):
    __tablename__ = "committee_databases"

    id = Column(Integer, primary_key=True)
    committee_id = Column(Integer, ForeignKey("committees.id"))
    row_data = Column(JSON)
    created_by = Column(Integer, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class MonthlyReport(Base):
    __tablename__ = "monthly_reports"

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("users.id"))
    file_url = Column(String)
    month = Column(String)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    target_type = Column(String)
    target_id = Column(Integer)
    comment = Column(String)
    is_reported = Column(Boolean, default=False)
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_deleted = Column(Boolean, default=False)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AccessPermission(Base):
    __tablename__ = "access_permissions"

    id = Column(Integer, primary_key=True)
    section_name = Column(String)
    committee_id = Column(Integer, ForeignKey("committees.id"))
    can_edit = Column(Boolean, default=False)
    granted_by = Column(Integer, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)