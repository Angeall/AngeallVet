import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)
security_scheme = HTTPBearer()


def verify_supabase_token(token: str) -> dict:
    """Verify and decode a Supabase JWT token."""
    if not settings.SUPABASE_JWT_SECRET:
        logger.error("SUPABASE_JWT_SECRET is not configured – all tokens will be rejected")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration serveur incomplète (JWT secret manquant)",
        )
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré",
        )
    except jwt.InvalidTokenError as e:
        logger.warning("JWT verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
        )


def _auto_provision_user(supabase_uid: str, db: Session):
    """Create a local profile for a Supabase user who doesn't have one yet."""
    from app.core.supabase import get_supabase_admin
    from app.models.user import User, UserRole

    try:
        sb = get_supabase_admin()
        sb_user = sb.auth.admin.get_user_by_id(supabase_uid)
    except Exception:
        logger.exception("Failed to fetch Supabase user %s for auto-provisioning", supabase_uid)
        raise HTTPException(
            status_code=401,
            detail="Profil utilisateur non trouvé. Contactez un administrateur.",
        )

    meta = sb_user.user.user_metadata or {}
    role_str = meta.get("role", UserRole.VETERINARIAN.value)
    try:
        role = UserRole(role_str)
    except ValueError:
        role = UserRole.VETERINARIAN

    user = User(
        supabase_uid=supabase_uid,
        email=sb_user.user.email,
        first_name=meta.get("first_name", ""),
        last_name=meta.get("last_name", ""),
        role=role,
        phone=meta.get("phone", None),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Auto-provisioned local profile for %s (%s)", user.email, user.role.value)
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
):
    """Extract user from Supabase JWT and find corresponding local profile."""
    from app.models.user import User

    payload = verify_supabase_token(credentials.credentials)
    supabase_uid = payload.get("sub")
    if not supabase_uid:
        raise HTTPException(status_code=401, detail="Token invalide: sub manquant")

    user = db.query(User).filter(User.supabase_uid == supabase_uid).first()
    if user is None:
        user = _auto_provision_user(supabase_uid, db)
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
