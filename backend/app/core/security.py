"""Application authentication.

PocketBase verifies credentials and issues a PB token; the backend exchanges
that token (see ``endpoints/auth``) for an *application JWT* signed with the
tenant's secret. This module mints and verifies those application JWTs and
exposes the ``get_current_user`` / ``require_roles`` dependencies.
"""
import hmac
import logging
import time

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_request_db
from app.core.tenancy import tenant_from_request

logger = logging.getLogger(__name__)
security_scheme = HTTPBearer()


def create_app_token(
    subject: str,
    secret: str,
    *,
    extra: dict | None = None,
    expires_minutes: int | None = None,
) -> str:
    """Mint an application JWT (HS256) signed with the tenant secret.

    ``subject`` is the PocketBase record id of the authenticated user.
    """
    now = int(time.time())
    exp_min = expires_minutes if expires_minutes is not None else settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES
    payload = {"sub": subject, "iat": now, "exp": now + exp_min * 60}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm=settings.AUTH_JWT_ALGORITHM)


def verify_app_token(token: str, secret: str) -> dict:
    """Verify an application JWT against the tenant secret."""
    try:
        return jwt.decode(token, secret, algorithms=[settings.AUTH_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expiré")
    except jwt.InvalidTokenError as e:
        logger.warning("Application JWT verification failed: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_request_db),
):
    """Resolve the authenticated user for the current tenant.

    The tenant is resolved up-front by the sub-domain middleware (stashed on the
    request scope), so ``db`` is already routed to the tenant database and the
    JWT is verified with the tenant's signing secret.
    """
    from app.models.user import User

    tenant = tenant_from_request(request)
    payload = verify_app_token(credentials.credentials, tenant.jwt_secret)
    pb_uid = payload.get("sub")
    if not pb_uid:
        raise HTTPException(status_code=401, detail="Token invalide: sub manquant")

    user = db.query(User).filter(User.pb_user_id == pb_uid).first()
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Profil utilisateur non trouvé. Contactez un administrateur.",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    return user


def require_roles(*roles):
    """Dependency that restricts access to specific roles."""
    def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droits insuffisants pour cette action",
            )
        return current_user
    return role_checker


def tenant_has_module(request: Request, module_key: str) -> bool:
    """True if the current request's tenant has the given paid module unlocked."""
    return module_key in tenant_from_request(request).modules


def require_module(module_key: str):
    """Dependency that gates an endpoint behind a paid module.

    This is the REAL lock: the entitlement comes from the tenant's signed license
    (resolved into ``TenantContext.modules``), never from anything the client can
    edit. Tampering with the frontend or calling the API directly changes
    nothing — without the module the request is refused with 403.
    """
    def checker(request: Request):
        from app.core.licensing import MODULE_LABELS

        if module_key not in tenant_from_request(request).modules:
            label = MODULE_LABELS.get(module_key, module_key)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Module « {label} » non activé pour votre clinique.",
            )
        return True

    return checker


def require_platform_admin(x_platform_admin_token: str = Header(default="")):
    """Guard for cross-tenant registry endpoints.

    Requires the ``X-Platform-Admin-Token`` header to match the configured
    ``PLATFORM_ADMIN_TOKEN``. This is a PLATFORM-level credential, deliberately
    separate from the per-tenant ADMIN role: a clinic admin must never be able
    to read or manage other tenants. Fails closed when no token is configured.
    """
    expected = settings.PLATFORM_ADMIN_TOKEN
    if not expected or not hmac.compare_digest(x_platform_admin_token or "", expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès plateforme refusé",
        )
    return True
