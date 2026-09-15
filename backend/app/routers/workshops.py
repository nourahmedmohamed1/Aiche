from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.workshop import Workshop, WorkshopSession
from app.schemas.workshop import WorkshopCreate, WorkshopOut, WorkshopSessionCreate, WorkshopSessionOut
from app.dependencies import get_current_user, get_user_permissions

router = APIRouter()


@router.get("", response_model=List[WorkshopOut])
@router.get("/", response_model=List[WorkshopOut])
def list_workshops(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all available workshops for viewing."""
    workshops = db.query(Workshop).all()
    result = []
    for w in workshops:
        w_out = WorkshopOut.model_validate(w)
        w_out.sessions_count = len(w.sessions) if hasattr(w, 'sessions') and w.sessions else db.query(WorkshopSession).filter(WorkshopSession.workshop_id == w.id).count()
        w_out.sessions = db.query(WorkshopSession).filter(WorkshopSession.workshop_id == w.id).all()
        result.append(w_out)
    return result


@router.get("/{workshop_id}", response_model=WorkshopOut)
def get_workshop(
    workshop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single workshop details including its sessions list."""
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")

    sessions = db.query(WorkshopSession).filter(WorkshopSession.workshop_id == workshop_id).all()
    w_out = WorkshopOut.model_validate(workshop)
    w_out.sessions_count = len(sessions)
    w_out.sessions = sessions
    return w_out


@router.post("", response_model=WorkshopOut, status_code=201)
@router.post("/", response_model=WorkshopOut, status_code=201)
def create_workshop(
    workshop_in: WorkshopCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new workshop. Requires `add_workshop` permission -> 403 if unauthorized."""
    perms = get_user_permissions(db, current_user)
    if not perms.get("add_workshop"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to add workshops"
        )

    new_workshop = Workshop(
        title=workshop_in.title,
        description=workshop_in.description,
        image_url=workshop_in.image_url,
        instructor=workshop_in.instructor,
        created_by=current_user.id
    )
    db.add(new_workshop)
    db.commit()
    db.refresh(new_workshop)

    w_out = WorkshopOut.model_validate(new_workshop)
    w_out.sessions_count = 0
    w_out.sessions = []
    return w_out


@router.put("/{workshop_id}", response_model=WorkshopOut)
def update_workshop(
    workshop_id: int,
    workshop_in: WorkshopCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a workshop. Requires `edit_workshop` permission -> 403 if unauthorized."""
    perms = get_user_permissions(db, current_user)
    if not perms.get("edit_workshop"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to edit workshops"
        )

    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")

    workshop.title = workshop_in.title
    workshop.description = workshop_in.description
    workshop.image_url = workshop_in.image_url
    workshop.instructor = workshop_in.instructor

    db.commit()
    db.refresh(workshop)
    
    sessions = db.query(WorkshopSession).filter(WorkshopSession.workshop_id == workshop_id).all()
    w_out = WorkshopOut.model_validate(workshop)
    w_out.sessions_count = len(sessions)
    w_out.sessions = sessions
    return w_out


@router.delete("/{workshop_id}", status_code=204)
def delete_workshop(
    workshop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a workshop. Requires `delete_workshop` permission -> 403 if unauthorized."""
    perms = get_user_permissions(db, current_user)
    if not perms.get("delete_workshop"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to delete workshops"
        )

    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")

    db.delete(workshop)
    db.commit()
    return None


# ── Workshop Sessions Sub-routes ─────────────────────────────────────────────

@router.get("/{workshop_id}/sessions", response_model=List[WorkshopSessionOut])
def list_workshop_sessions(
    workshop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List sessions for a specific workshop."""
    sessions = db.query(WorkshopSession).filter(WorkshopSession.workshop_id == workshop_id).all()
    return sessions


@router.post("/{workshop_id}/sessions", response_model=WorkshopSessionOut, status_code=201)
def add_workshop_session(
    workshop_id: int,
    session_in: WorkshopSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a session to a workshop. Requires `add_workshop` permission -> 403 if unauthorized."""
    perms = get_user_permissions(db, current_user)
    if not perms.get("add_workshop"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to add workshop sessions"
        )

    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")

    new_session = WorkshopSession(
        workshop_id=workshop_id,
        title=session_in.title,
        description=session_in.description,
        date=session_in.date,
        mode=session_in.mode,
        location_or_link=session_in.location_or_link,
        materials_url=session_in.materials_url
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


@router.delete("/{workshop_id}/sessions/{session_id}", status_code=204)
def delete_workshop_session(
    workshop_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a workshop session. Requires `edit_workshop` permission -> 403 if unauthorized."""
    perms = get_user_permissions(db, current_user)
    if not perms.get("edit_workshop"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to delete workshop sessions"
        )

    session = db.query(WorkshopSession).filter(
        WorkshopSession.id == session_id,
        WorkshopSession.workshop_id == workshop_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Workshop session not found")

    db.delete(session)
    db.commit()
    return None
