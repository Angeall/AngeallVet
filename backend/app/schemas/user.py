from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole = UserRole.ASSISTANT
    phone: Optional[str] = None


class UserCreate(UserBase):
    """Create user: password is managed by Supabase, we just need profile info."""
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    supabase_uid: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# Role permissions
class RolePermissionUpdate(BaseModel):
    permissions: Dict[str, bool]


class RolePermissionResponse(BaseModel):
    role: str
    permissions: Dict[str, bool]

    class Config:
        from_attributes = True


# Notifications
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: Optional[str] = None
    notification_type: str
    is_read: bool
    link: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
