from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    VETERINARIAN = "veterinarian"
    ASSISTANT = "assistant"
    ACCOUNTANT = "accountant"
    GUEST = "guest"


# Default permissions per role
DEFAULT_PERMISSIONS = {
    "admin": {
        "dashboard": True, "clients": True, "animals": True, "agenda": True,
        "waiting_room": True, "medical": True, "inventory": True,
        "invoices": True, "estimates": True, "sales": True,
        "hospitalization": True, "communications": True, "users": True, "stats": True,
    },
    "veterinarian": {
        "dashboard": True, "clients": True, "animals": True, "agenda": True,
        "waiting_room": True, "medical": True, "inventory": True,
        "invoices": True, "estimates": True, "sales": True,
        "hospitalization": True, "communications": True, "users": False, "stats": True,
    },
    "assistant": {
        "dashboard": True, "clients": True, "animals": True, "agenda": True,
        "waiting_room": True, "medical": False, "inventory": True,
        "invoices": True, "estimates": True, "sales": True,
        "hospitalization": True, "communications": True, "users": False, "stats": False,
    },
    "accountant": {
        "dashboard": True, "clients": True, "animals": False, "agenda": False,
        "waiting_room": False, "medical": False, "inventory": True,
        "invoices": True, "estimates": True, "sales": True,
        "hospitalization": False, "communications": False, "users": False, "stats": True,
    },
    "guest": {
        "dashboard": True, "clients": False, "animals": False, "agenda": True,
        "waiting_room": True, "medical": False, "inventory": False,
        "invoices": False, "estimates": False, "sales": False,
        "hospitalization": False, "communications": False, "users": False, "stats": False,
    },
}


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(SAEnum(UserRole), nullable=False, unique=True)
    permissions = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(String(1000))
    notification_type = Column(String(50), default="info")  # info, waiting_room, alert
    is_read = Column(Boolean, default=False)
    link = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    supabase_uid = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.ASSISTANT)
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    google_calendar_token = Column(String(500))
    sidenav_color = Column(String(7))  # hex color e.g. "#1e3a5f"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant")
