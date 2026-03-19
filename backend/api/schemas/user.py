from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field
from api.models.user import UserRole
from api.schemas.common import BaseSchema


class UserBase(BaseSchema):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    invite_code: Optional[str] = None


class UserLogin(BaseSchema):
    email: EmailStr
    password: str


class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None


class ChangePassword(BaseSchema):
    old_password: str
    new_password: str = Field(..., min_length=8)


class UserResponse(BaseSchema):
    id: UUID
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class InviteCreate(BaseSchema):
    email: Optional[EmailStr] = None
    max_uses: int = Field(default=1, ge=1)
    expires_at: Optional[datetime] = None


class InviteResponse(BaseSchema):
    id: UUID
    code: str
    email: Optional[str]
    max_uses: int
    used_count: int
    expires_at: Optional[datetime]
    created_at: datetime
