"""Tenant resolution and per-request tenant context.

A request is mapped to a tenant by the sub-domain of ``settings.BASE_DOMAIN``.
The resolved :class:`TenantContext` is stashed on the ASGI ``scope`` by the
``TenantMiddleware`` (see ``app.main``) and read back from ``request.scope`` by
the DB/auth dependencies.

We deliberately read the tenant from the request *scope* (a plain dict passed by
reference through the ASGI chain) rather than a ``ContextVar``: values set in a
Starlette middleware do not reliably propagate to endpoints running in the
thread-pool, whereas the scope always does.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TenantContext:
    """Everything the request needs to know about its tenant."""

    slug: str
    # None -> use the central/default database (single-clinic / dev / tests)
    db_url: Optional[str]
    pocketbase_url: str
    pb_admin_email: str
    pb_admin_password: str
    jwt_secret: str
    is_default: bool = False
    # Paid modules unlocked for this tenant (from its signed license). Read by
    # the ``require_module`` dependency to gate paid endpoints server-side.
    modules: frozenset = frozenset()


def derive_tenant_secret(slug: str) -> str:
    """Per-tenant JWT signing secret derived from APP_SECRET_KEY + slug.

    Stable, unique per tenant and never stored. A tenant row may override it
    via its ``auth_jwt_secret`` column.
    """
    return hmac.new(
        settings.APP_SECRET_KEY.encode(),
        f"tenant:{slug}".encode(),
        hashlib.sha256,
    ).hexdigest()


def default_tenant_context() -> TenantContext:
    """Context for the default tenant (no sub-domain matched).

    This is the path used by the common "one Docker stack per clinic" model:
    the clinic's modules come from the signed ``LICENSE`` in its own ``.env``.
    """
    from app.core.licensing import resolve_modules

    slug = settings.DEFAULT_TENANT_SLUG
    return TenantContext(
        slug=slug,
        db_url=None,
        pocketbase_url=settings.POCKETBASE_URL,
        pb_admin_email=settings.POCKETBASE_ADMIN_EMAIL,
        pb_admin_password=settings.POCKETBASE_ADMIN_PASSWORD,
        jwt_secret=derive_tenant_secret(slug),
        is_default=True,
        modules=resolve_modules(slug, settings.LICENSE),
    )


def extract_subdomain(host: str) -> Optional[str]:
    """Return the tenant sub-domain from a Host header, or None.

    ``clinique-martin.angeallvet.fr`` -> ``clinique-martin``.
    Returns None for the bare domain, IPs, localhost, testserver and the
    reserved labels (www/app/api/pb).
    """
    if not host:
        return None
    # X-Forwarded-Host may contain a comma-separated list; keep the first.
    host = host.split(",")[0].strip().split(":")[0].lower()
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "testserver", "backend"):
        return None
    if host.replace(".", "").isdigit():  # raw IPv4
        return None
    base = settings.BASE_DOMAIN.lower()
    if host == base:
        return None
    if host.endswith("." + base):
        sub = host[: -(len(base) + 1)].split(".")[0]
        if sub in ("", "www", "app", "api", "pb"):
            return None
        return sub
    return None


def _context_from_tenant(t) -> TenantContext:
    from app.core.licensing import resolve_modules

    # A central stack serving several tenants stores each tenant's signed license
    # on its registry row (``tenants.license``); a per-clinic stack uses the
    # default-tenant path above instead.
    return TenantContext(
        slug=t.slug,
        db_url=t.database_url,
        pocketbase_url=t.pocketbase_url or settings.POCKETBASE_URL,
        pb_admin_email=t.pb_admin_email or settings.POCKETBASE_ADMIN_EMAIL,
        pb_admin_password=t.pb_admin_password or settings.POCKETBASE_ADMIN_PASSWORD,
        jwt_secret=derive_tenant_secret(t.slug),
        is_default=False,
        modules=resolve_modules(t.slug, getattr(t, "license", "") or ""),
    )


def _lookup_tenant(field: str, value: str) -> Optional[TenantContext]:
    """Query the central registry for an active tenant. Returns None on any
    error (table missing, no connection, no match) so callers fall back to the
    default tenant gracefully."""
    try:
        from app.core.database import _default_session_factory
        from app.models.tenant import Tenant

        db = _default_session_factory()
        try:
            col = getattr(Tenant, field)
            t = (
                db.query(Tenant)
                .filter(col == value, Tenant.is_active == True)  # noqa: E712
                .first()
            )
            return _context_from_tenant(t) if t else None
        finally:
            db.close()
    except Exception as e:  # pragma: no cover - defensive
        logger.debug("Tenant lookup failed for %s=%s: %s", field, value, e)
        return None


def resolve_tenant_context(host: str) -> TenantContext:
    """Resolve a tenant from a request Host header. Falls back to default."""
    sub = extract_subdomain(host)
    if not sub:
        return default_tenant_context()
    return _lookup_tenant("subdomain", sub) or _lookup_tenant("slug", sub) or default_tenant_context()


def resolve_tenant_by_slug(slug: str) -> TenantContext:
    """Resolve a tenant directly by slug (used by the X-Tenant-Slug override)."""
    if not slug or slug == settings.DEFAULT_TENANT_SLUG:
        return default_tenant_context()
    return _lookup_tenant("slug", slug) or _lookup_tenant("subdomain", slug) or default_tenant_context()


def tenant_from_request(request) -> TenantContext:
    """Read the TenantContext stashed on the ASGI scope by the middleware."""
    ctx = request.scope.get("tenant_ctx")
    return ctx if ctx is not None else default_tenant_context()
