from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.course import Certificate, Course
from app.models.workshop import Workshop
from app.dependencies import get_current_user
from app.utils.certificate_generator import generate_personalized_certificate_png

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
    source_type: str  # "course" or "workshop"
    source_id: int


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
    Triggers dynamic PNG certificate creation for a completed course or workshop.
    Uploads the certificate to Google Drive and saves the shareable URL.
    """
    import os
    from app.utils.certificate_generator import CERTIFICATES_DIR
    from app.utils.drive_uploader import upload_to_drive

    title = "Continuous Learning Program"
    if req.source_type == "course":
        c = db.query(Course).filter(Course.id == req.source_id).first()
        if c:
            title = c.title
    elif req.source_type == "workshop":
        w = db.query(Workshop).filter(Workshop.id == req.source_id).first()
        if w:
            title = w.title

    filename = f"cert_{req.source_type}_{req.source_id}_user_{current_user.id}.png"

    # 1. Generate personalized PNG image
    img_url = generate_personalized_certificate_png(
        user_full_name=current_user.full_name,
        title=title,
        source_type=req.source_type,
        source_id=req.source_id,
        user_id=current_user.id
    )

    file_path = os.path.join(CERTIFICATES_DIR, filename)

    try:
        # 2. Upload to Google Drive
        drive_url = upload_to_drive(file_path, filename)

        # 3. Delete local file post-upload if uploaded to Drive
        if drive_url != img_url and os.path.exists(file_path):
            os.remove(file_path)

        # 4. Save to database
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
                pdf_url=drive_url
            )
            db.add(cert)
        else:
            cert.pdf_url = drive_url

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
