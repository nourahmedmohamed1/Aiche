"""
routers/feedback.py  –  Member B
Endpoints for the Feedback & Moderation system (Sections 48-49, Rules 7-8).

Endpoints:
  POST   /api/feedback              — Leave feedback [Student/Member]
  GET    /api/feedback               — List feedback for a target [Public]
  GET    /api/feedback/reported      — List reported feedback [President/VP/Secretary]
  POST   /api/feedback/{id}/report  — Flag a comment for review [OC / Admin]
  DELETE /api/feedback/{id}         — Approve deletion + remove author [President/VP]

Design notes:
  • The report → delete flow is deliberately two-step:
    1. OC flags a comment  (report_feedback in core_logic.py)
    2. President/VP approves removal (delete_reported_feedback in core_logic.py)
  • Deletion is atomic: the comment AND the author's account are removed in
    a single transaction (Rule 8).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.point import Feedback
from app.models.user import User
from app.schemas.point import FeedbackCreate, FeedbackOut
from app.dependencies import get_current_user, require_role
from app.core_logic import report_feedback, delete_reported_feedback

router = APIRouter()


@router.post("/", response_model=FeedbackOut, status_code=201)
def leave_feedback(
    data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Leave feedback on a course/workshop/event/site visit.
    Any logged-in user can post feedback — user_id is taken from the JWT.
    """
    fb = Feedback(
        user_id=current_user.id,
        target_type=data.target_type,
        target_id=data.target_id,
        comment=data.comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@router.get("/", response_model=list[FeedbackOut])
def list_feedback(
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    List feedback, optionally filtered by target_type and/or target_id.
    Public endpoint — no auth required so guests can read reviews.
    Only returns non-deleted feedback.
    """
    query = db.query(Feedback).filter(Feedback.is_deleted == False)  # noqa: E712
    if target_type:
        query = query.filter(Feedback.target_type == target_type)
    if target_id is not None:
        query = query.filter(Feedback.target_id == target_id)
    return query.order_by(Feedback.created_at.desc()).all()


@router.get("/reported", response_model=list[FeedbackOut])
def list_reported_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "president", "vice_president", "secretary"
    )),
):
    """
    List all reported (flagged) but not-yet-deleted feedback.
    Only visible to President/VP/Secretary — this IS the review queue.
    """
    return (
        db.query(Feedback)
        .filter(Feedback.is_reported == True, Feedback.is_deleted == False)  # noqa: E712
        .order_by(Feedback.created_at.desc())
        .all()
    )


@router.post("/{feedback_id}/report")
def flag_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "committee_admin", "president", "vice_president", "secretary"
    )),
):
    """
    OC or any admin flags a comment for President/VP review.
    The comment stays visible — this just adds it to the moderation queue.
    """
    fb = report_feedback(db, feedback_id, current_user)
    if not fb:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback not found")
    return {"message": "Feedback reported", "is_reported": True}


@router.delete("/{feedback_id}")
def approve_feedback_deletion(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "president", "vice_president"
    )),
):
    """
    President/VP approves removal — deletes the comment AND the author's
    account together in one atomic transaction (Rule 8).
    """
    success = delete_reported_feedback(db, feedback_id, current_user)
    if not success:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback not found")
    return {"message": "Comment and account deleted"}
