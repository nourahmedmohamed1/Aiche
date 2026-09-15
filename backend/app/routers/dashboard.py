from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.user import User, RoleEnum
from app.models.course import Course
from app.models.workshop import Workshop
from app.models.event import EventSiteVisit
from app.models.session import CommitteeSession
from app.dependencies import get_current_user

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns live statistics counts for the Dashboard based on current user access.
    """
    total_students = db.query(User).filter(User.role == RoleEnum.student).count()
    total_members = db.query(User).filter(User.role != RoleEnum.student).count()
    total_courses = db.query(Course).count()
    total_workshops = db.query(Workshop).count()
    
    total_events = db.query(EventSiteVisit).filter(EventSiteVisit.type == "event").count()
    total_site_visits = db.query(EventSiteVisit).filter(EventSiteVisit.type == "site_visit").count()

    return {
        "students": total_students,
        "members": total_members,
        "courses": total_courses,
        "workshops": total_workshops,
        "events": total_events,
        "site_visits": total_site_visits
    }


@router.get("/recent-activity")
def get_recent_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns recent system activity stream formatted with committee identity.
    """
    activities = []

    # 1. Recent sessions
    recent_sessions = db.query(CommitteeSession).order_by(desc(CommitteeSession.id)).limit(5).all()
    for s in recent_sessions:
        comm_name = s.committee.name if s.committee else "Committee"
        activities.append({
            "id": f"session_{s.id}",
            "type": "session",
            "message": f"{comm_name} Committee added a new session: '{s.title}'",
            "created_at": s.created_at.isoformat() if hasattr(s, 'created_at') and s.created_at else None
        })

    # 2. Recent courses
    recent_courses = db.query(Course).order_by(desc(Course.id)).limit(5).all()
    for c in recent_courses:
        activities.append({
            "id": f"course_{c.id}",
            "type": "course",
            "message": f"New course added: '{c.title}'",
            "created_at": None
        })

    # 3. Recent student enrollments / signups
    recent_students = db.query(User).order_by(desc(User.id)).limit(5).all()
    for u in recent_students:
        activities.append({
            "id": f"user_{u.id}",
            "type": "student",
            "message": f"New user signed up: '{u.full_name}'",
            "created_at": u.created_at.isoformat() if u.created_at else None
        })

    return activities[:10]
