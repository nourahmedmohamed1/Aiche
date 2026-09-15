"""
routers/database_routes.py  –  Member B
Endpoints for the Committee Database feature (Sections 44-47 of the baseline).

Endpoints:
  GET  /api/committees/{id}/database — View any committee's data [Any logged-in]
  POST /api/committees/{id}/database — Add a row [Owning committee / granted]

Design notes:
  • Any logged-in user can VIEW any committee's database (Rule 4: view-all).
  • Only the owning committee (or one explicitly granted access via
    AccessPermissions) can WRITE — enforced by has_edit_access() from
    dependencies.py (Section 8.3).
  • The row_data column is flexible JSON, so each committee can have totally
    different "columns" without needing a separate SQL table per committee.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.point import CommitteeDatabaseRow
from app.models.user import User
from app.schemas.point import CommitteeDatabaseCreate, CommitteeDatabaseOut
from app.dependencies import get_current_user, has_edit_access

router = APIRouter()


@router.get("/{committee_id}/database", response_model=list[CommitteeDatabaseOut])
def list_committee_database(
    committee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    View any committee's database rows — open to all logged-in users (Rule 4).
    """
    return (
        db.query(CommitteeDatabaseRow)
        .filter(CommitteeDatabaseRow.committee_id == committee_id)
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
    Only the owning committee or one explicitly granted edit access can write.
    """
    # Check edit permissions — combines role check + committee ownership +
    # AccessPermission overrides in one call.
    if not has_edit_access(db, current_user, "database"):
        # Additionally allow if the user belongs to the target committee.
        if current_user.committee_id != committee_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    row = CommitteeDatabaseRow(
        committee_id=committee_id,
        row_data=data.row_data,
        created_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
