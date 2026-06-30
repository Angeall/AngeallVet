from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.crypto import EncryptedSecret


class Tenant(Base):
    """Represents a clinic / organisation (tenant) in the multi-tenant system.

    Each tenant has its own PostgreSQL database. The central database holds
    only the tenants and users tables. All clinic data lives in the tenant's
    dedicated database.
    """
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    # Encrypted at rest (pgcrypto) — contains the tenant DB password.
    database_url = Column(EncryptedSecret, nullable=False)

    # --- Auth (tenant-local PocketBase) ---
    # Sub-domain used to route requests to this tenant
    # (e.g. "clinique-martin" for clinique-martin.angeallvet.fr).
    subdomain = Column(String(100), unique=True, nullable=True, index=True)
    # Internal URL of this tenant's PocketBase instance (Docker service name).
    pocketbase_url = Column(String(500), nullable=True)
    pb_admin_email = Column(String(255), nullable=True)
    # PocketBase superuser password — encrypted at rest (pgcrypto).
    pb_admin_password = Column(EncryptedSecret, nullable=True)
    # NB: the per-tenant application-JWT secret is always DERIVED from
    # APP_SECRET_KEY + slug (see core.tenancy), never stored.

    # Signed paid-module license for this tenant (Ed25519 JWT). Not secret: it is
    # public-verifiable and grants nothing without the deployer's private key.
    # Used only by the central multi-tenant stack; a per-clinic stack reads its
    # license from the LICENSE env var instead. See app/core/licensing.
    license = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
