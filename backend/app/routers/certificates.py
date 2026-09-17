from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.course import Certificate, Course
from app.models.workshop import Workshop
from app.dependencies import get_current_user, get_user_permissions
from app.utils.certificate_generator import generate_personalized_certificate_png

# For validation
from app.models.course import CourseProgress, CoursePart
from app.models.workshop import WorkshopSession, WorkshopAttendance
from app.models.event import EventSiteVisit, EventAttendance
from app.models.session import CommitteeSession, SessionScoring

router = APIRouter()


class CertificateOut(BaseModel):
    id: int
    user_id: int
    type: str
    source_id: int
    pdf_url: str
    issued_at: datetime

    class Config:
        from_attributes = True


class GenerateCertRequest(BaseModel):
    source_type: str  # "course", "workshop", "event", "session"
    source_id: int

class ManualCertRequest(BaseModel):
    username: str
    title: str


@router.get("", response_model=List[CertificateOut])
@router.get("/", response_model=List[CertificateOut])
def list_my_certificates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all certificates earned by the current user."""
    certificates = db.query(Certificate).filter(Certificate.user_id == current_user.id).all()
    return certificates


@router.get("/{certificate_id}", response_model=CertificateOut)
def get_certificate(
    certificate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get certificate details by ID."""
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return cert


@router.post("/generate", response_model=CertificateOut, status_code=201)
def generate_certificate(
    req: GenerateCertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers dynamic PNG certificate creation ONLY IF the user has successfully
    completed the course, workshop, event, or session.
    Uploads the certificate to Cloud and saves the shareable URL.
    """
    import os
    from app.utils.certificate_generator import CERTIFICATES_DIR
    from app.utils.cloudinary_uploader import upload_to_cloudinary
    from app.utils.drive_uploader import upload_to_drive

    title = ""

    # 1. Validate Completion & Get Title
    if req.source_type == "course":
        from app.core_logic import check_and_issue_course_certificate
        cert = check_and_issue_course_certificate(db, current_user.id, req.source_id)
        if not cert:
            raise HTTPException(status_code=400, detail="Course not completed or not found")
        return cert

    elif req.source_type == "workshop":
        w = db.query(Workshop).filter(Workshop.id == req.source_id).first()
        if not w:
            raise HTTPException(status_code=404, detail="Workshop not found")
        # Check if attended any session in this workshop
        sessions = db.query(WorkshopSession).filter(WorkshopSession.workshop_id == w.id).all()
        if not sessions:
            raise HTTPException(status_code=400, detail="Workshop has no sessions to attend")
        
        attended = False
        for s in sessions:
            att = db.query(WorkshopAttendance).filter_by(
                workshop_session_id=s.id, user_id=current_user.id, status="present"
            ).first()
            if att:
                attended = True
                break
        
        if not attended:
            raise HTTPException(status_code=400, detail="You must attend the workshop to get a certificate")
        title = w.title

    elif req.source_type == "event":
        e = db.query(EventSiteVisit).filter(EventSiteVisit.id == req.source_id).first()
        if not e:
            raise HTTPException(status_code=404, detail="Event not found")
        
        att = db.query(EventAttendance).filter_by(
            event_id=req.source_id, user_id=current_user.id, status="attended"
        ).first()
        if not att:
            raise HTTPException(status_code=400, detail="You must attend the event to get a certificate")
        title = e.title

    elif req.source_type == "session":
        s = db.query(CommitteeSession).filter(CommitteeSession.id == req.source_id).first()
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        
        score = db.query(SessionScoring).filter_by(
            session_id=req.source_id, user_id=current_user.id, attendance_status="attended"
        ).first()
        if not score:
            raise HTTPException(status_code=400, detail="You must attend the session to get a certificate")
        title = s.title

    else:
        raise HTTPException(status_code=400, detail="Invalid source_type")

    # 2. Proceed with generating and saving the certificate
    filename = f"cert_{req.source_type}_{req.source_id}_user_{current_user.id}.png"

    img_url = generate_personalized_certificate_png(
        user_full_name=current_user.full_name,
        title=title,
        source_type=req.source_type,
        source_id=req.source_id,
        user_id=current_user.id
    )

    file_path = os.path.join(CERTIFICATES_DIR, filename)

    try:
        if os.getenv("CLOUDINARY_URL") or os.getenv("CLOUDINARY_CLOUD_NAME"):
            cloud_url = upload_to_cloudinary(file_path, filename)
        else:
            cloud_url = upload_to_drive(file_path, filename)

        if cloud_url != img_url and os.path.exists(file_path):
            os.remove(file_path)

        cert = db.query(Certificate).filter_by(
            user_id=current_user.id,
            type=req.source_type,
            source_id=req.source_id
        ).first()

        if not cert:
            cert = Certificate(
                user_id=current_user.id,
                type=req.source_type,
                source_id=req.source_id,
                pdf_url=cloud_url
            )
            db.add(cert)
        else:
            cert.pdf_url = cloud_url

        db.commit()
        db.refresh(cert)
        return cert
    except Exception as e:
        db.rollback()
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Certificate generation failed: {str(e)}"
        )


@router.post("/manual", response_model=CertificateOut, status_code=201)
def generate_manual_certificate(
    req: ManualCertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Allows committee heads and admins to manually issue custom certificates to users.
    """
    if current_user.role not in ("committee_admin", "president", "vice_president", "secretary"):
        raise HTTPException(status_code=403, detail="Forbidden: You do not have permission to issue manual certificates")

    target_user = db.query(User).filter(User.username == req.username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    import os
    import time
    from app.utils.certificate_generator import CERTIFICATES_DIR, generate_personalized_certificate_png
    from app.utils.cloudinary_uploader import upload_to_cloudinary
    from app.utils.drive_uploader import upload_to_drive

    # Using timestamp for unique source_id to avoid overriding
    unique_source_id = int(time.time())
    
    filename = f"cert_manual_{unique_source_id}_user_{target_user.id}.png"

    img_url = generate_personalized_certificate_png(
        user_full_name=target_user.full_name,
        title=req.title,
        source_type="manual",
        source_id=unique_source_id,
        user_id=target_user.id
    )

    file_path = os.path.join(CERTIFICATES_DIR, filename)

    try:
        if os.getenv("CLOUDINARY_URL") or os.getenv("CLOUDINARY_CLOUD_NAME"):
            cloud_url = upload_to_cloudinary(file_path, filename)
        else:
            cloud_url = upload_to_drive(file_path, filename)

        if cloud_url != img_url and os.path.exists(file_path):
            os.remove(file_path)

        cert = Certificate(
            user_id=target_user.id,
            type="manual",
            source_id=unique_source_id,
            pdf_url=cloud_url
        )
        db.add(cert)
        db.commit()
        db.refresh(cert)
        return cert
    except Exception as e:
        db.rollback()
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual certificate generation failed: {str(e)}"
        )
