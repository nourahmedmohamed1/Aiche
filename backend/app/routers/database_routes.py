"""
routers/database_routes.py  –  Member B
Endpoints for the Committee Database feature (Sections 44-47 of the baseline).

Endpoints:
  GET    /api/committees/{id}/database — View any committee's data (paginated) [Any logged-in]
  POST   /api/committees/{id}/database — Add a row [Owning committee / granted]
  PUT    /api/committees/{id}/database/{row_id} — Edit a row [Owning committee / granted]
  DELETE /api/committees/{id}/database/{row_id} — Delete a row [Owning committee / granted]
"""

import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.point import CommitteeDatabaseRow
from app.models.user import User
from app.schemas.point import (
    CommitteeDatabaseCreate,
    CommitteeDatabaseUpdate,
    CommitteeDatabaseOut,
)
from app.dependencies import get_current_user, has_edit_access

router = APIRouter()


def _check_database_edit_access(db: Session, current_user: User, committee_id: int):
    """
    Re-checks edit access for a committee database section.
    Allowed if the user has global database edit access (President/VP/Secretary or AccessPermission)
    OR if the user belongs to the target committee.
    """
    if not has_edit_access(db, current_user, "database"):
        if current_user.committee_id != committee_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not allowed to edit this committee's database")


@router.get("/{committee_id}/database", response_model=list[CommitteeDatabaseOut])
def list_committee_database(
    committee_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    View any committee's database rows — open to all logged-in users.
    Supports pagination via `skip` and `limit`.
    """
    return (
        db.query(CommitteeDatabaseRow)
        .filter(CommitteeDatabaseRow.committee_id == committee_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/{committee_id}/database", response_model=CommitteeDatabaseOut, status_code=201)
def add_database_row(
    committee_id: int,
    data: CommitteeDatabaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a row to a committee's database.
    Validates that row_data is a JSON object.
    Only the owning committee or one explicitly granted edit access can write.
    """
    _check_database_edit_access(db, current_user, committee_id)

    if not isinstance(data.row_data, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="row_data must be a JSON object")

    row = CommitteeDatabaseRow(
        committee_id=committee_id,
        row_data=data.row_data,
        created_by=current_user.id,
        updated_at=datetime.datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/{committee_id}/database/{row_id}", response_model=CommitteeDatabaseOut)
def update_database_row(
    committee_id: int,
    row_id: int,
    data: CommitteeDatabaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Edit an existing database row.
    Re-checks has_edit_access() and updates `updated_at`.
    """
    _check_database_edit_access(db, current_user, committee_id)

    row = db.query(CommitteeDatabaseRow).filter(
        CommitteeDatabaseRow.id == row_id,
        CommitteeDatabaseRow.committee_id == committee_id
    ).first()

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Database row not found")

    if not isinstance(data.row_data, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="row_data must be a JSON object")

    row.row_data = data.row_data
    row.updated_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(row)
    return row


@router.delete("/{committee_id}/database/{row_id}", status_code=204)
def delete_database_row(
    committee_id: int,
    row_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a database row.
    Re-checks has_edit_access().
    """
    _check_database_edit_access(db, current_user, committee_id)

    row = db.query(CommitteeDatabaseRow).filter(
        CommitteeDatabaseRow.id == row_id,
        CommitteeDatabaseRow.committee_id == committee_id
    ).first()

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Database row not found")

    db.delete(row)
    db.commit()
    return None
