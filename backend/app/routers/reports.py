"""
routers/reports.py  –  Member B
Endpoint for Monthly Reports (Section 42 of the baseline).

Endpoints:
  POST /api/reports/members/{id}/monthly-report — Upload a report [QC only]
  GET  /api/reports/members/{id}                — List reports for a member [Member+]

Design notes:
  • Only QC can upload monthly reports (per Section 42: "QC uploads it, not
    the member").  We enforce this by checking the committee name, not just
    the role, since QC is technically a committee_admin.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.point import MonthlyReport
from app.models.user import User
from app.schemas.point import MonthlyReportCreate, MonthlyReportOut
from app.dependencies import get_current_user, require_role

router = APIRouter()


@router.post(
    "/members/{member_id}/monthly-report",
    response_model=MonthlyReportOut,
    status_code=201,
)
def upload_monthly_report(
    member_id: int,
    data: MonthlyReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "committee_admin", "president", "vice_president", "secretary"
    )),
):
    """
    QC uploads a report directly into a specific Member's profile.
    Restricted to QC committee admins (checked via committee name)
    and President/VP/Secretary.
    """
    # Additional QC check for committee_admin role — presidents etc. bypass.
    if current_user.role == "committee_admin":
        if not current_user.committee or current_user.committee.name != "QC":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Only QC can upload monthly reports"
            )

    report = MonthlyReport(
        member_id=member_id,
        file_url=data.file_url,
        month=data.month,
        uploaded_by=current_user.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get(
    "/members/{member_id}",
    response_model=list[MonthlyReportOut],
)
def list_member_reports(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "member", "committee_admin", "president", "vice_president", "secretary"
    )),
):
    """List all monthly reports for a specific member."""
    return (
        db.query(MonthlyReport)
        .filter(MonthlyReport.member_id == member_id)
        .order_by(MonthlyReport.uploaded_at.desc())
        .all()
    )
