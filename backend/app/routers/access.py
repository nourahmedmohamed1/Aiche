"""
routers/access.py  –  Member B
Endpoint for the Committee Access Control system (Section 7 of the baseline).

Endpoints:
  POST /api/access-permissions — Grant/revoke edit access [President/VP/Secretary]
  GET  /api/access-permissions — List all access permissions [President/VP/Secretary]

Design notes:
  • This is the ONLY endpoint that writes to the access_permissions table.
  • All other routers check permissions via has_edit_access() in
    dependencies.py, which reads this table — so granting access here
    immediately takes effect everywhere, with zero code changes needed.
  • Uses upsert logic: if a permission row already exists for the same
    (section_name, committee_id) pair, it updates instead of duplicating.
"""

import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.point import AccessPermission
from app.models.user import User
from app.schemas.point import AccessPermissionCreate, AccessPermissionOut
from app.dependencies import require_role

router = APIRouter()


@router.post("/", response_model=AccessPermissionOut)
def set_access_permission(
    data: AccessPermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "president", "vice_president", "secretary"
    )),
):
    """
    Grant or revoke a committee's edit access to a named section.
    Uses upsert: if a matching row exists, it's updated; otherwise a new
    row is created.  This means calling this endpoint twice with the same
    section_name + committee_id just toggles can_edit, never duplicates.
    """
    # Check for existing permission row (upsert pattern).
    existing = db.query(AccessPermission).filter_by(
        section_name=data.section_name,
        committee_id=data.committee_id,
    ).first()

    if existing:
        # Update the existing row.
        existing.can_edit = data.can_edit
        existing.granted_by = current_user.id
        existing.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    # Create a new permission row.
    permission = AccessPermission(
        section_name=data.section_name,
        committee_id=data.committee_id,
        can_edit=data.can_edit,
        granted_by=current_user.id,
    )
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


@router.get("/", response_model=list[AccessPermissionOut])
def list_access_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "president", "vice_president", "secretary"
    )),
):
    """List all access permission records — admin oversight."""
    return db.query(AccessPermission).all()
