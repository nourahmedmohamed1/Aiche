from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    password: str
    # No `role` or `committee_id` here on purpose — a signup can NEVER set its own
    # role or committee; that's enforced at the schema level, not just by convention.


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    full_name: str
    username: str
    email: str
    role: str
    committee_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
        # Lets Pydantic build this schema directly from a SQLAlchemy model object.


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"