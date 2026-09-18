from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.course import Course, CoursePart, CourseProgress
from app.schemas.course import CourseCreate, CourseOut, CoursePartCreate, CoursePartOut
from app.dependencies import get_current_user, get_user_permissions

router = APIRouter()


@router.get("", response_model=List[CourseOut])
@router.get("/", response_model=List[CourseOut])
def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all available courses for viewing."""
    courses = db.query(Course).all()
    result = []
    for c in courses:
        student_count = db.query(CourseProgress.user_id).filter(
            CourseProgress.course_part_id.in_([p.id for p in c.parts])
        ).distinct().count() if c.parts else 0

        course_out = CourseOut.model_validate(c)
        course_out.students = student_count
        result.append(course_out)
    return result


@router.get("/{course_id}", response_model=CourseOut)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single course details including student count and parts list."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    student_count = db.query(CourseProgress.user_id).filter(
        CourseProgress.course_part_id.in_([p.id for p in course.parts])
    ).distinct().count() if course.parts else 0

    course_out = CourseOut.model_validate(course)
    course_out.students = student_count
    return course_out


@router.post("", response_model=CourseOut, status_code=201)
@router.post("/", response_model=CourseOut, status_code=201)
def create_course(
    course_in: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new course. Requires `add_course` permission -> 403 if unauthorized."""
    perms = get_user_permissions(db, current_user)
    if not perms.get("add_course"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to add courses"
        )

    new_course = Course(
        title=course_in.title,
        description=course_in.description,
        image_url=course_in.image_url,
        instructor=course_in.instructor,
        level=course_in.level,
        duration=course_in.duration,
        created_by=current_user.id
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    
    course_out = CourseOut.model_validate(new_course)
    course_out.students = 0
    return course_out


@router.put("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: int,
    course_in: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a course. Requires `edit_course` permission -> 403 if unauthorized."""
    perms = get_user_permissions(db, current_user)
    if not perms.get("edit_course"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to edit courses"
        )

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    course.title = course_in.title
    course.description = course_in.description
    course.image_url = course_in.image_url
    course.instructor = course_in.instructor
    course.level = course_in.level
    course.duration = course_in.duration

    db.commit()
    db.refresh(course)
    return CourseOut.model_validate(course)


@router.delete("/{course_id}", status_code=204)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a course. Requires `delete_course` permission -> 403 if unauthorized."""
    perms = get_user_permissions(db, current_user)
    if not perms.get("delete_course"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to delete courses"
        )

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    db.delete(course)
    db.commit()
    return None


# ── Course Parts Sub-routes ──────────────────────────────────────────────────

@router.get("/{course_id}/parts", response_model=List[CoursePartOut])
def list_course_parts(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List parts for a specific course."""
    parts = db.query(CoursePart).filter(CoursePart.course_id == course_id).order_by(CoursePart.order_index).all()
    return parts


@router.post("/{course_id}/parts", response_model=CoursePartOut, status_code=201)
def add_course_part(
    course_id: int,
    part_in: CoursePartCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a part to a course. Requires `add_course_part` permission -> 403 if unauthorized."""
    perms = get_user_permissions(db, current_user)
    if not perms.get("add_course_part"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to add course parts"
        )

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    new_part = CoursePart(
        course_id=course_id,
        title=part_in.title,
        type=part_in.type,
        order_index=part_in.order_index,
        content_url=part_in.content_url
    )
    db.add(new_part)
    db.commit()
    db.refresh(new_part)
    return new_part


@router.delete("/{course_id}/parts/{part_id}", status_code=204)
def delete_course_part(
    course_id: int,
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a course part. Requires `edit_course` / `add_course_part` permission -> 403 if unauthorized."""
    perms = get_user_permissions(db, current_user)
    if not perms.get("add_course_part"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to delete course parts"
        )

    part = db.query(CoursePart).filter(CoursePart.id == part_id, CoursePart.course_id == course_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Course part not found")

    db.delete(part)
    db.commit()
    return None


@router.post("/course-parts/{part_id}/complete")
@router.post("/{course_id}/parts/{part_id}/complete")
def complete_part(
    part_id: int,
    course_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a course part completed for the current user.
    Enforces sequential unlock rule: part cannot be completed until the previous part is done.
    If part is a task, awards +2 points. Automatically issues course certificate when all parts are done.
    """
    import datetime
    from app.core_logic import is_part_unlocked, check_and_issue_course_certificate, add_point_entry
    from app.models.course import ProgressStatus, PartType

    part = db.query(CoursePart).filter(CoursePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Course part not found")

    if not is_part_unlocked(db, current_user.id, part):
        raise HTTPException(status_code=403, detail="Previous part not completed yet")

    progress = db.query(CourseProgress).filter_by(user_id=current_user.id, course_part_id=part_id).first()
    if not progress:
        progress = CourseProgress(
            user_id=current_user.id,
            course_part_id=part_id,
            status=ProgressStatus.completed,
            completion_type="online",
            completed_at=datetime.datetime.utcnow(),
        )
        db.add(progress)
    else:
        progress.status = ProgressStatus.completed
        progress.completion_type = "online"
        progress.completed_at = datetime.datetime.utcnow()

    # Award points if part is task
    if part.type == "task" or part.type == PartType.task:
        add_point_entry(db, current_user.id, "task", progress.id or part_id, 2, "Task submitted on time")

    db.commit()

    # Auto-issue certificate if all parts completed
    try:
        check_and_issue_course_certificate(db, current_user.id, part.course_id)
    except Exception:
        pass

    return {"message": "Part completed"}
