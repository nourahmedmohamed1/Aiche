from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.database import Base
import enum, datetime


class RoleEnum(str, enum.Enum):
    student = "student"
    member = "member"
    committee_admin = "committee_admin"
    president = "president"
    vice_president = "vice_president"
    secretary = "secretary"


class Committee(Base):
    __tablename__ = "committees"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    login_email = Column(String, unique=True)

    users = relationship("User", back_populates="committee")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(Enum(RoleEnum), default=RoleEnum.student)
    committee_id = Column(Integer, ForeignKey("committees.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    committee = relationship("Committee", back_populates="users")