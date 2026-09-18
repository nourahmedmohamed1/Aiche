import os, datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from passlib.context import CryptContext

from dotenv import load_dotenv
from app.database import get_db
from app.models.user import User

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET_KEY") or "default_secret_key_change_in_production"
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


import bcrypt


def hash_password(password: str) -> str:
    pwd_bytes = password[:72].encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain[:72].encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def create_access_token(data: dict, expires_minutes: int = 1440):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*allowed_roles):
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        return current_user
    return checker


from app.models.point import AccessPermission


def has_edit_access(db: Session, current_user: User, section_name: str) -> bool:
    if current_user.role in ("president", "vice_president", "secretary"):
        return True
    permission = db.query(AccessPermission).filter_by(
        section_name=section_name, committee_id=current_user.committee_id).first()
    return permission is not None and permission.can_edit


def get_user_permissions(db: Session, user: User) -> dict:
    role = user.role.value if hasattr(user.role, 'value') else str(user.role)
    committee_name = user.committee.name if user.committee else None

    if role in ("president", "vice_president", "secretary"):
        return {
            "view_courses": True,
            "add_course": True,
            "edit_course": True,
            "delete_course": True,
            "add_course_part": True,
            "view_workshops": True,
            "add_workshop": True,
            "edit_workshop": True,
            "delete_workshop": True,
            "view_certificates": True,
        }

    is_technical = committee_name in ("Technical", "Web Development")
    can_add_course = is_technical or has_edit_access(db, user, "courses")
    can_add_workshop = (role == "committee_admin") or has_edit_access(db, user, "workshops")

    if role == "committee_admin":
        return {
            "view_courses": True,
            "add_course": can_add_course,
            "edit_course": can_add_course,
            "delete_course": can_add_course,
            "add_course_part": can_add_course,
            "view_workshops": True,
            "add_workshop": can_add_workshop,
            "edit_workshop": can_add_workshop,
            "delete_workshop": can_add_workshop,
            "view_certificates": True,
        }

    return {
        "view_courses": True,
        "add_course": False,
        "edit_course": False,
        "delete_course": False,
        "add_course_part": False,
        "view_workshops": True,
        "add_workshop": False,
        "edit_workshop": False,
        "delete_workshop": False,
        "view_certificates": True,
    }