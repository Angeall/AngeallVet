import logging

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_central_db

logger = logging.getLogger(__name__)
security_scheme = HTTPBearer()

# Lazily-initialised JWKS client for asymmetric (RS256) verification.
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    """Return a cached PyJWKClient pointed at the Supabase JWKS endpoint."""
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
        logger.info("Initialised JWKS client → %s", jwks_url)
    return _jwks_client


def verify_supabase_token(token: str) -> dict:
    """Verify and decode a Supabase JWT token.

    Strategy:
    1. Peek at the token header to determine the algorithm (RS256 vs HS256).
    2. RS256 → fetch the public key from the Supabase JWKS endpoint.
       HS256 → use the shared SUPABASE_JWT_SECRET (legacy / self-hosted).
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.exceptions.DecodeError as e:
        logger.warning("Cannot read JWT header: %s", e)
        raise HTTPException(status_code=401, detail="Token invalide")

    alg = header.get("alg", "HS256")

    try:
        if alg.startswith("RS") or alg.startswith("ES"):
            # Asymmetric – use the JWKS endpoint
            if not settings.SUPABASE_URL:
                logger.error("SUPABASE_URL is required for asymmetric JWT verification")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Configuration serveur incomplète (SUPABASE_URL manquant)",
                )
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",
            )
        else:
            # Symmetric (HS256) – legacy / self-hosted Supabase
            if not settings.SUPABASE_JWT_SECRET:
                logger.error("SUPABASE_JWT_SECRET is required for HS256 JWT verification")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Configuration serveur incomplète (JWT secret manquant)",
                )
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
        logger.warning("JWT verification failed (alg=%s): %s", alg, e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during JWT verification: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la vérification du token",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_central_db),
):
    """Extract user from Supabase JWT, find local profile, and route to tenant DB.

    Users must be explicitly created by an admin via /auth/register.
    A valid Supabase token alone is NOT enough — a matching local profile is required.
    """
    from app.models.user import User
    from app.models.tenant import Tenant
    from app.core.database import set_tenant_db_url

    payload = verify_supabase_token(credentials.credentials)
    supabase_uid = payload.get("sub")
    if not supabase_uid:
        raise HTTPException(status_code=401, detail="Token invalide: sub manquant")

    user = db.query(User).filter(User.supabase_uid == supabase_uid).first()
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Profil utilisateur non trouvé. Contactez un administrateur.",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    # Resolve tenant and set the tenant database URL for all downstream queries
    if user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if tenant and tenant.is_active and tenant.database_url:
            set_tenant_db_url(tenant.database_url)

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
