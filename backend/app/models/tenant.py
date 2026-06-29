from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class Tenant(Base):
    """Represents a clinic / organisation (tenant) in the multi-tenant system.

    Each tenant has its own PostgreSQL database. The central database holds
    only the tenants and users tables. All clinic data lives in the tenant's
    dedicated database.
    """
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    database_url = Column(String(500), nullable=False)

    # --- Auth (tenant-local PocketBase) ---
    # Sub-domain used to route requests to this tenant
    # (e.g. "clinique-martin" for clinique-martin.angeallvet.fr).
    subdomain = Column(String(100), unique=True, nullable=True, index=True)
    # Internal URL of this tenant's PocketBase instance (Docker service name).
    pocketbase_url = Column(String(500), nullable=True)
    # PocketBase superuser credentials used by the backend to manage users.
    # NOTE: should be encrypted at rest in production (see ENCRYPTION_KEY).
    pb_admin_email = Column(String(255), nullable=True)
    pb_admin_password = Column(String(255), nullable=True)
    # Optional override for the per-tenant application-JWT signing secret.
    # When NULL, the secret is derived from APP_SECRET_KEY + slug.
    auth_jwt_secret = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
