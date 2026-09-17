"""
core_logic.py  –  Shared business-rule functions (Section 9 of the guide).

This file centralises the 5 trickiest rules so routers stay thin and testable.
Member A owns: is_part_unlocked(), check_and_issue_course_certificate()
Member B owns: get_total_points(), add_point_entry(), get_visible_sessions(),
               report_feedback(), delete_reported_feedback()

Why one file instead of two?  Both members' routers call add_point_entry(),
so splitting into separate files would cause circular imports.  Keeping
everything here keeps the dependency graph simple.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.course import CoursePart, CourseProgress, Certificate
from app.models.point import PointEntry, Feedback
from app.models.session import CommitteeSession
from app.models.user import User


# ═══════════════════════════════════════════════════════════════════════════════
#  Member A — Learning Track (stubs included so Member A can fill them in)
# ═══════════════════════════════════════════════════════════════════════════════

def is_part_unlocked(db: Session, user_id: int, part: CoursePart) -> bool:
    """
    Section 9.1 — Sequential course unlock.
    Returns True if the student is allowed to open this course part.
    Rule: "A part cannot be opened until the previous part is completed."
    """
    if part.order_index == 1:
        # The very first part is always open — nothing before it to check.
        return True

    # Find the part immediately before this one in the same course.
    previous = db.query(CoursePart).filter(
        CoursePart.course_id == part.course_id,
        CoursePart.order_index == part.order_index - 1
    ).first()

    # Check whether THIS student has completed that previous part.
    progress = db.query(CourseProgress).filter_by(
        user_id=user_id, course_part_id=previous.id
    ).first()

    return progress is not None and progress.status == "completed"


def check_and_issue_course_certificate(db: Session, user_id: int, course_id: int):
    """
    Section 9.3 — Course certificate generation.
    Issues a certificate once ALL parts of the course show status = "completed"
    for this student. Returns the Certificate row, or None if not yet earned.
    Uploads the generated certificate to Google Drive and stores the shareable link.
    """
    parts = db.query(CoursePart).filter_by(course_id=course_id).all()
    if not parts:
        return None

    all_completed = all(
        db.query(CourseProgress).filter_by(
            user_id=user_id, course_part_id=part.id, status="completed"
        ).first() is not None
        for part in parts
    )

    if not all_completed:
        return None

    # Check if certificate already exists (idempotent — don't duplicate).
    existing = db.query(Certificate).filter_by(
        user_id=user_id, type="course", source_id=course_id
    ).first()
    if existing:
        return existing

    from app.models.course import Course
    from app.utils.certificate_generator import generate_personalized_certificate_png, CERTIFICATES_DIR
    from app.utils.cloudinary_uploader import upload_to_cloudinary
    from app.utils.drive_uploader import upload_to_drive
    import os

    user = db.query(User).filter(User.id == user_id).first()
    course = db.query(Course).filter(Course.id == course_id).first()
    user_name = user.full_name if user else f"User {user_id}"
    course_title = course.title if course else f"Course {course_id}"

    # 1. Generate local PNG certificate
    filename = f"cert_course_{course_id}_user_{user_id}.png"
    local_rel_url = generate_personalized_certificate_png(
        user_full_name=user_name,
        title=course_title,
        source_type="course",
        source_id=course_id,
        user_id=user_id,
    )

    file_path = os.path.join(CERTIFICATES_DIR, filename)

    try:
        # 2. Upload to Cloudinary (or Google Drive if Cloudinary credentials not set)
        if os.getenv("CLOUDINARY_URL") or os.getenv("CLOUDINARY_CLOUD_NAME"):
            cloud_url = upload_to_cloudinary(file_path, filename)
        else:
            cloud_url = upload_to_drive(file_path, filename)

        # 3. Delete local file after upload if uploaded to Cloud
        if cloud_url != local_rel_url and os.path.exists(file_path):
            os.remove(file_path)

        # 4. Save Certificate row to database
        certificate = Certificate(
            user_id=user_id,
            type="course",
            source_id=course_id,
            pdf_url=cloud_url,
        )
        db.add(certificate)
        db.commit()
        db.refresh(certificate)
        return certificate
    except Exception as e:
        db.rollback()
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise RuntimeError(f"Failed to issue course certificate: {str(e)}") from e


# ═══════════════════════════════════════════════════════════════════════════════
#  Member B — Community & Operations Track
# ═══════════════════════════════════════════════════════════════════════════════

# ── 9.2  Total Points — always a live SUM, never a stored editable number ────

def get_total_points(db: Session, user_id: int) -> int:
    """
    Section 9.2 — Returns the live sum of all point_entries for a given user.
    The baseline is explicit: "Total Points is NOT entered manually — it is
    calculated automatically."  We push the SUM to the database (fast even
    with thousands of rows) rather than pulling every row into Python.
    """
    total = db.query(func.sum(PointEntry.points)).filter(
        PointEntry.user_id == user_id
    ).scalar()
    # SQL SUM() returns None when there are zero matching rows, so we
    # normalise that to 0 for a cleaner caller experience.
    return total or 0


def add_point_entry(
    db: Session,
    user_id: int,
    source_type: str,
    source_id: int,
    points: int,
    reason: str,
) -> PointEntry:
    """
    Section 9.2 — The ONE function every router calls whenever points change.
    Centralising this means the point_entries table is always written to
    consistently, and every point can be traced back to its source.

    IMPORTANT: This function deliberately does NOT call db.commit().
    The calling router is expected to commit once at the end, after all its
    own changes are staged, so everything saves together atomically.
    """
    entry = PointEntry(
        user_id=user_id,
        source_type=source_type,
        source_id=source_id,
        points=points,
        reason=reason,
    )
    db.add(entry)
    return entry


# ── 9.4  Session visibility ─────────────────────────────────────────────────

def get_visible_sessions(db: Session, current_user: User) -> list:
    """
    Section 9.4 — Returns only the sessions this user is allowed to see.
    Rule: "A Member sees only their own committee's Sessions + Public Sessions,
    EXCEPT QC, who sees every committee's Sessions."
    """
    # QC special case (Section 33 of the baseline).
    if (current_user.role == "committee_admin"
            and current_user.committee
            and current_user.committee.name == "QC"):
        return db.query(CommitteeSession).all()

    # President / VP / Secretary see everything (full oversight per Section 2.6).
    if current_user.role in ("president", "vice_president", "secretary"):
        return db.query(CommitteeSession).all()

    # Normal member / committee_admin: own committee + public sessions.
    return db.query(CommitteeSession).filter(
        (CommitteeSession.visibility == "public")
        | (CommitteeSession.committee_id == current_user.committee_id)
    ).all()


# ── 9.5  Feedback report → delete flow ──────────────────────────────────────

def report_feedback(db: Session, feedback_id: int, reporter: User) -> Feedback:
    """
    Section 9.5, Step 1 — OC flags a comment for President/VP review.
    The comment stays visible; this just adds it to the review queue.
    """
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        return None
    fb.is_reported = True
    fb.reported_by = reporter.id
    db.commit()
    db.refresh(fb)
    return fb


def delete_reported_feedback(db: Session, feedback_id: int, approver: User) -> bool:
    """
    Section 9.5, Step 2 — President/VP approves removal.
    Deletes the comment AND the author's account together in a single
    committed transaction (the baseline's Rule 8 requirement: "all or nothing").
    """
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        return False

    # Find the author of the offending comment.
    author = db.query(User).filter(User.id == fb.user_id).first()

    # Soft-delete the feedback (preserve a record of what was said).
    fb.is_deleted = True
    fb.deleted_by = approver.id

    # Hard-delete the author's account.
    if author:
        db.delete(author)

    # ONE commit saves both changes atomically — if anything fails between
    # the two operations, NEITHER change is saved.
    db.commit()
    return True
