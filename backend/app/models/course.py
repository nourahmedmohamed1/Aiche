from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Enum
from sqlalchemy.orm import relationship
from app.database import Base
import enum, datetime


class PartType(str, enum.Enum):
    lecture = "lecture"
    task = "task"
    quiz = "quiz"
    final_exam = "final_exam"


class ProgressStatus(str, enum.Enum):
    locked = "locked"
    in_progress = "in_progress"
    completed = "completed"


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    image_url = Column(String)
    instructor = Column(String)
    level = Column(String)
    duration = Column(String)
    created_by = Column(Integer, ForeignKey("users.id"))

    parts = relationship("CoursePart", back_populates="course",
                          order_by="CoursePart.order_index")


class CoursePart(Base):
    __tablename__ = "course_parts"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    type = Column(Enum(PartType))
    order_index = Column(Integer)
    title = Column(String)
    content_url = Column(String, nullable=True)

    course = relationship("Course", back_populates="parts")


class CourseProgress(Base):
    __tablename__ = "course_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_part_id = Column(Integer, ForeignKey("course_parts.id"))
    status = Column(Enum(ProgressStatus), default=ProgressStatus.locked)
    completion_type = Column(String, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String)
    source_id = Column(Integer)
    grade = Column(Float, nullable=True)
    pdf_url = Column(String)
    issued_at = Column(DateTime, default=datetime.datetime.utcnow)