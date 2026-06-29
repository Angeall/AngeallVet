"""Thin PocketBase REST client used by the backend.

Each tenant runs its own PocketBase instance. The backend talks to it over the
internal Docker network (service name), never the public sub-domain. We use
``httpx`` directly (already a dependency) rather than a PocketBase SDK to keep
the surface minimal.

Auth model:
* The browser authenticates against PocketBase directly and obtains a PB token.
* The backend *verifies* that token via ``auth-refresh`` (PocketBase tokens
  cannot be validated offline — each record has its own signing key), then mints
  its own per-tenant application JWT.
* User management (create / update / delete) is performed with a PocketBase
  *superuser* token obtained from the tenant's admin credentials.
"""
from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0)
_SUPERUSERS = "_superusers"


def _users(collection: str | None = None) -> str:
    return collection or settings.POCKETBASE_USERS_COLLECTION


def pb_auth_with_password(pb_url: str, identity: str, password: str, collection: str | None = None):
    """Authenticate an end-user. Returns (token, record). Raises 401 on failure."""
    url = f"{pb_url}/api/collections/{_users(collection)}/auth-with-password"
    try:
        r = httpx.post(url, json={"identity": identity, "password": password}, timeout=_TIMEOUT)
    except httpx.HTTPError as e:
        logger.error("PocketBase unreachable at %s: %s", pb_url, e)
        raise HTTPException(status_code=503, detail="Service d'authentification indisponible")
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    data = r.json()
    return data["token"], data["record"]


def pb_verify_token(pb_url: str, token: str, collection: str | None = None):
    """Verify a PocketBase end-user token via auth-refresh.

    Returns (fresh_token, record). Raises 401 if the token is invalid/expired.
    """
    url = f"{pb_url}/api/collections/{_users(collection)}/auth-refresh"
    try:
        r = httpx.post(url, headers={"Authorization": token}, timeout=_TIMEOUT)
    except httpx.HTTPError as e:
        logger.error("PocketBase unreachable at %s: %s", pb_url, e)
        raise HTTPException(status_code=503, detail="Service d'authentification indisponible")
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Jeton PocketBase invalide ou expiré")
    data = r.json()
    return data["token"], data["record"]


def pb_admin_token(pb_url: str, admin_email: str, admin_password: str) -> str:
    """Obtain a PocketBase superuser token for user-management operations."""
    if not admin_email or not admin_password:
        raise HTTPException(
            status_code=500,
            detail="Configuration PocketBase incomplète (admin manquant pour ce tenant)",
        )
    url = f"{pb_url}/api/collections/{_SUPERUSERS}/auth-with-password"
    try:
        r = httpx.post(url, json={"identity": admin_email, "password": admin_password}, timeout=_TIMEOUT)
    except httpx.HTTPError as e:
        logger.error("PocketBase unreachable at %s: %s", pb_url, e)
        raise HTTPException(status_code=503, detail="Service d'authentification indisponible")
    if r.status_code != 200:
        logger.error("PocketBase superuser auth failed (%s): %s", r.status_code, r.text)
        raise HTTPException(status_code=500, detail="Échec de l'authentification administrateur PocketBase")
    return r.json()["token"]


def pb_create_user(
    pb_url: str,
    admin_token: str,
    email: str,
    password: str,
    name: str = "",
    collection: str | None = None,
) -> dict:
    """Create a PocketBase auth record. Returns the created record."""
    url = f"{pb_url}/api/collections/{_users(collection)}/records"
    payload = {
        "email": email,
        "password": password,
        "passwordConfirm": password,
        "emailVisibility": True,
        "verified": True,
        "name": name,
    }
    try:
        r = httpx.post(url, headers={"Authorization": admin_token}, json=payload, timeout=_TIMEOUT)
    except httpx.HTTPError as e:
        logger.error("PocketBase unreachable at %s: %s", pb_url, e)
        raise HTTPException(status_code=503, detail="Service d'authentification indisponible")
    if r.status_code not in (200, 201):
        logger.warning("PocketBase create user failed (%s): %s", r.status_code, r.text)
        detail = "Erreur PocketBase lors de la création de l'utilisateur"
        if r.status_code == 400 and "email" in r.text.lower():
            detail = "Email déjà utilisé dans PocketBase"
        raise HTTPException(status_code=400, detail=detail)
    return r.json()


def pb_update_user(
    pb_url: str,
    admin_token: str,
    record_id: str,
    patch: dict,
    collection: str | None = None,
) -> dict:
    """Patch a PocketBase auth record (email / name / password)."""
    url = f"{pb_url}/api/collections/{_users(collection)}/records/{record_id}"
    try:
        r = httpx.patch(url, headers={"Authorization": admin_token}, json=patch, timeout=_TIMEOUT)
    except httpx.HTTPError as e:
        logger.error("PocketBase unreachable at %s: %s", pb_url, e)
        raise HTTPException(status_code=503, detail="Service d'authentification indisponible")
    if r.status_code != 200:
        logger.warning("PocketBase update user failed (%s): %s", r.status_code, r.text)
        raise HTTPException(status_code=400, detail="Erreur PocketBase lors de la mise à jour de l'utilisateur")
    return r.json()


def pb_delete_user(pb_url: str, admin_token: str, record_id: str, collection: str | None = None) -> None:
    """Delete a PocketBase auth record (best-effort)."""
    url = f"{pb_url}/api/collections/{_users(collection)}/records/{record_id}"
    try:
        httpx.delete(url, headers={"Authorization": admin_token}, timeout=_TIMEOUT)
    except httpx.HTTPError as e:  # pragma: no cover - best effort
        logger.warning("PocketBase delete user failed: %s", e)
