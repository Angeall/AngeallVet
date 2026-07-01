import logging
import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.security import require_permission

logger = logging.getLogger(__name__)
from app.core.database import Base, _default_engine as engine, _default_session_factory
from app.api.endpoints import (
    auth, clients, animals, appointments,
    medical, inventory, billing, communication, hospitalization,
    controlled_substances, associations, billing_rules, exports, invoice_sync,
    agenda, accounting, vaccination,
)
from app.api.endpoints import settings as settings_endpoints


async def _reject_unknown_tenant(send):
    """Send a 404 for a request whose Host maps to no known tenant (strict mode)."""
    body = b'{"detail":"Tenant inconnu"}'
    await send({
        "type": "http.response.start",
        "status": 404,
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
    })
    await send({"type": "http.response.body", "body": body})


class TenantMiddleware:
    """Pure-ASGI middleware: resolve the tenant from the Host sub-domain.

    The resolved :class:`~app.core.tenancy.TenantContext` is stashed on the ASGI
    ``scope`` so the DB/auth dependencies can route to the right tenant database,
    PocketBase instance and JWT secret. Implemented as pure ASGI (not
    ``BaseHTTPMiddleware``) so the value reliably reaches thread-pool endpoints.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)
        from app.core.tenancy import resolve_tenant_context, resolve_tenant_by_slug

        headers = {k.decode().lower(): v.decode() for k, v in (scope.get("headers") or [])}
        host = headers.get("x-forwarded-host") or headers.get("host") or ""
        # The X-Tenant-Slug override lets a client pick any tenant, so it is a
        # dev/testing convenience only — ignored in production, where the tenant
        # MUST come from the (proxy-validated) Host. Caddy also strips it inbound.
        slug = headers.get("x-tenant-slug") if settings.is_dev_env else None
        if slug:
            ctx = resolve_tenant_by_slug(slug)
        else:
            # Strict only for a central multi-tenant stack: an unknown sub-domain
            # is rejected rather than silently served the default/central DB.
            ctx = resolve_tenant_context(host, strict=settings.MULTI_TENANT and not settings.is_dev_env)
        if ctx is None:
            return await _reject_unknown_tenant(send)
        scope["tenant_ctx"] = ctx
        return await self.app(scope, receive, send)


# OpenAPI docs (Swagger / ReDoc / schema) are exposed only in dev — disabled in
# production so the API surface isn't published.
app = FastAPI(
    title=settings.APP_NAME,
    description="Système de gestion pour cliniques vétérinaires (PMS)",
    version="1.0.0",
    docs_url="/api/docs" if settings.is_dev_env else None,
    redoc_url="/api/redoc" if settings.is_dev_env else None,
    openapi_url="/openapi.json" if settings.is_dev_env else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve the tenant (sub-domain) for every request before routing.
app.add_middleware(TenantMiddleware)

# Reject requests with an unexpected Host in production when a trusted-host
# allow-list is configured (defense-in-depth against Host/X-Forwarded-Host
# spoofing; Caddy already resets those headers at the edge). Added last so it is
# the outermost layer and runs before tenant resolution.
if not settings.is_dev_env and settings.trusted_hosts_list:
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions so they return a proper JSON response
    that passes through the CORS middleware (instead of a bare 500)."""
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur"},
    )


# API routes
API_PREFIX = "/api/v1"
# Section-access matrix (H1): mutating requests in a section require the role to
# have that section enabled (require_permission gates writes only — GET reads stay
# open so cross-section lookups keep working). Routers with public endpoints
# (agenda ical/oauth, communication unsubscribe) or their own stricter role gate
# (billing_rules, controlled_substances, accounting, users, settings) are gated
# at the endpoint level instead.
def _perm(section):
    return [Depends(require_permission(section))]


app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(clients.router, prefix=API_PREFIX, dependencies=_perm("clients"))
app.include_router(animals.router, prefix=API_PREFIX, dependencies=_perm("animals"))
app.include_router(appointments.router, prefix=API_PREFIX, dependencies=_perm("agenda"))
app.include_router(medical.router, prefix=API_PREFIX, dependencies=_perm("medical"))
app.include_router(inventory.router, prefix=API_PREFIX, dependencies=_perm("inventory"))
app.include_router(billing.router, prefix=API_PREFIX, dependencies=_perm("invoices"))
app.include_router(billing_rules.router, prefix=API_PREFIX)
app.include_router(exports.router, prefix=API_PREFIX)
app.include_router(invoice_sync.router, prefix=API_PREFIX)
app.include_router(communication.router, prefix=API_PREFIX)
app.include_router(hospitalization.router, prefix=API_PREFIX, dependencies=_perm("hospitalization"))
app.include_router(settings_endpoints.router, prefix=API_PREFIX)
app.include_router(controlled_substances.router, prefix=API_PREFIX)
app.include_router(associations.router, prefix=API_PREFIX, dependencies=_perm("animals"))
app.include_router(agenda.router, prefix=API_PREFIX)
app.include_router(accounting.router, prefix=API_PREFIX)
app.include_router(vaccination.router, prefix=API_PREFIX, dependencies=_perm("animals"))

# Ensure the upload directory exists. Files are NOT exposed via a public static
# mount: medical attachments are sensitive (RGPD) and are streamed through an
# authenticated endpoint instead (see endpoints/medical.py).
upload_dir = settings.UPLOAD_DIR
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir, exist_ok=True)


def _ensure_schema(db_engine):
    """Ensure all tables and columns exist in the given database.

    create_all only creates missing tables — it won't ALTER existing ones.
    So we also run raw DDL for recently added columns that may be missing
    on databases that existed before the model change.
    """
    from sqlalchemy import text, inspect

    Base.metadata.create_all(bind=db_engine)

    # Column additions that create_all won't handle for pre-existing tables.
    # Each entry: (table, column, DDL to add it).
    _pending_columns = [
        ("animals", "vital_status", "ALTER TABLE animals ADD COLUMN vital_status VARCHAR(20) NOT NULL DEFAULT 'alive'"),
        ("animals", "vital_status_date", "ALTER TABLE animals ADD COLUMN vital_status_date DATE"),
        ("products", "is_shortcut", "ALTER TABLE products ADD COLUMN is_shortcut BOOLEAN NOT NULL DEFAULT false"),
        ("clients", "vat_number", "ALTER TABLE clients ADD COLUMN vat_number VARCHAR(50)"),
        ("products", "is_controlled_substance", "ALTER TABLE products ADD COLUMN is_controlled_substance BOOLEAN NOT NULL DEFAULT false"),
        ("animals", "association_id", "ALTER TABLE animals ADD COLUMN association_id INTEGER REFERENCES associations(id)"),
        ("reminder_rules", "postal_template", "ALTER TABLE reminder_rules ADD COLUMN postal_template TEXT"),
        ("medical_record_products", "treatment_location", "ALTER TABLE medical_record_products ADD COLUMN treatment_location VARCHAR(20) NOT NULL DEFAULT 'home'"),
        ("consultation_templates", "home_treatment", "ALTER TABLE consultation_templates ADD COLUMN home_treatment TEXT"),
        ("controlled_substance_entries", "dosage", "ALTER TABLE controlled_substance_entries ADD COLUMN dosage VARCHAR(200)"),
        ("controlled_substance_entries", "total_delivered", "ALTER TABLE controlled_substance_entries ADD COLUMN total_delivered NUMERIC(10,2)"),
        ("users", "sidenav_color", "ALTER TABLE users ADD COLUMN sidenav_color VARCHAR(7)"),
        ("users", "billing_program_id", "ALTER TABLE users ADD COLUMN billing_program_id INTEGER"),
        ("users", "ical_token", "ALTER TABLE users ADD COLUMN ical_token VARCHAR(64)"),
        ("billing_rules", "rule_type", "ALTER TABLE billing_rules ADD COLUMN rule_type VARCHAR(20) NOT NULL DEFAULT 'components'"),
        ("billing_rules", "tier_basis", "ALTER TABLE billing_rules ADD COLUMN tier_basis VARCHAR(20)"),
        ("clinic_settings", "invoice_ninja_url", "ALTER TABLE clinic_settings ADD COLUMN invoice_ninja_url VARCHAR(500)"),
        ("clinic_settings", "invoice_ninja_token", "ALTER TABLE clinic_settings ADD COLUMN invoice_ninja_token VARCHAR(255)"),
        ("clinic_settings", "allow_cross_vet_invoice_edit", "ALTER TABLE clinic_settings ADD COLUMN allow_cross_vet_invoice_edit BOOLEAN NOT NULL DEFAULT TRUE"),
        ("clients", "invoice_ninja_client_id", "ALTER TABLE clients ADD COLUMN invoice_ninja_client_id VARCHAR(64)"),
        ("invoices", "invoice_ninja_invoice_id", "ALTER TABLE invoices ADD COLUMN invoice_ninja_invoice_id VARCHAR(64)"),
        ("clients", "accepts_reminders", "ALTER TABLE clients ADD COLUMN accepts_reminders BOOLEAN NOT NULL DEFAULT true"),
        ("clients", "unsubscribe_token", "ALTER TABLE clients ADD COLUMN unsubscribe_token VARCHAR(64)"),
        ("invoices", "medical_record_id", "ALTER TABLE invoices ADD COLUMN medical_record_id INTEGER REFERENCES medical_records(id)"),
        ("invoice_lines", "lot_number", "ALTER TABLE invoice_lines ADD COLUMN lot_number VARCHAR(100)"),
        ("medical_record_products", "lot_number", "ALTER TABLE medical_record_products ADD COLUMN lot_number VARCHAR(100)"),
        ("medical_records", "pharmacy_prescription", "ALTER TABLE medical_records ADD COLUMN pharmacy_prescription TEXT"),
        ("medical_records", "context", "ALTER TABLE medical_records ADD COLUMN context TEXT"),
        # PocketBase auth / sub-domain tenancy (central registry).
        # Secret columns (database_url, pb_admin_password) are managed by
        # migration 008 (pgcrypto); auth_jwt_secret is no longer stored.
        ("tenants", "subdomain", "ALTER TABLE tenants ADD COLUMN subdomain VARCHAR(100)"),
        ("tenants", "pocketbase_url", "ALTER TABLE tenants ADD COLUMN pocketbase_url VARCHAR(500)"),
        ("tenants", "pb_admin_email", "ALTER TABLE tenants ADD COLUMN pb_admin_email VARCHAR(255)"),
        ("tenants", "license", "ALTER TABLE tenants ADD COLUMN license TEXT"),
    ]

    # Column renames that create_all won't perform on pre-existing tables.
    # Each entry: (table, old_column, new_column).
    _pending_renames = [
        ("users", "supabase_uid", "pb_user_id"),
    ]
    with db_engine.connect() as conn:
        inspector = inspect(db_engine)
        for table, column, ddl in _pending_columns:
            if table not in inspector.get_table_names():
                continue
            existing = [c["name"] for c in inspector.get_columns(table)]
            if column not in existing:
                conn.execute(text(ddl))
                logger.info("Added missing column %s.%s", table, column)
        for table, old, new in _pending_renames:
            if table not in inspector.get_table_names():
                continue
            cols = [c["name"] for c in inspector.get_columns(table)]
            if old in cols and new not in cols:
                conn.execute(text(f"ALTER TABLE {table} RENAME COLUMN {old} TO {new}"))
                logger.info("Renamed column %s.%s -> %s", table, old, new)
        conn.commit()

    # Performance indexes (PostgreSQL only). Runs in AUTOCOMMIT so one failing
    # statement (e.g. pg_trgm not permitted) does not abort the others.
    if db_engine.dialect.name == "postgresql":
        from app.core.db_indexes import PG_TRGM_EXTENSION, PERF_INDEXES

        tables = set(inspect(db_engine).get_table_names())
        statements = (
            [PG_TRGM_EXTENSION]
            + [ddl for t, ddl in PERF_INDEXES if t in tables]
            # Drop the now-redundant per-PK indexes (the PK is already indexed).
            + [f"DROP INDEX IF EXISTS ix_{t}_id" for t in tables]
        )
        with db_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as ac:
            for stmt in statements:
                try:
                    ac.execute(text(stmt))
                except Exception as e:
                    logger.warning("Index step skipped: %s", e)


@app.on_event("startup")
def on_startup():
    # 0. Fail closed on insecure production configuration.
    _insecure_secrets = {
        "",
        "dev-secret-key",
        "change-me-to-a-random-secret-key-in-production",
    }
    _is_prod = not settings.is_dev_env
    if _is_prod and settings.APP_SECRET_KEY in _insecure_secrets:
        raise RuntimeError(
            "APP_SECRET_KEY must be set to a strong, unique value in production "
            "(it derives every tenant's JWT signing secret)."
        )
    if _is_prod and not settings.ENCRYPTION_KEY:
        raise RuntimeError(
            "ENCRYPTION_KEY must be set in production: without it, tenant secrets "
            "(DB passwords, PocketBase superuser password, Google OAuth refresh "
            "tokens) would be stored in cleartext."
        )

    # 1. Ensure central database schema is up to date (tables + missing columns)
    try:
        _ensure_schema(engine)
        logger.info("Central database schema verified")
    except Exception as e:
        logger.error("Failed to ensure central schema: %s", e)

    # 2. Run Alembic migrations
    from alembic.config import Config
    from alembic import command

    alembic_ini = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
    if os.path.exists(alembic_ini):
        alembic_cfg = Config(alembic_ini)
        try:
            command.upgrade(alembic_cfg, "head")
            logger.info("Database migrations applied successfully")
        except Exception as e:
            logger.warning("Migration warning (non-blocking): %s", e)

    # 3. Ensure tenant databases also have the latest schema
    from sqlalchemy import create_engine as _ce
    try:
        central = _default_session_factory()
        from app.models.tenant import Tenant
        tenants = central.query(Tenant).filter(Tenant.is_active == True).all()
        for t in tenants:
            if t.database_url:
                try:
                    tenant_engine = _ce(t.database_url, pool_pre_ping=True)
                    _ensure_schema(tenant_engine)
                    tenant_engine.dispose()
                    logger.info("Schema updated for tenant %s", t.slug)
                except Exception as e:
                    logger.warning("Failed to update schema for tenant %s: %s", t.slug, e)
        central.close()
    except Exception as e:
        logger.warning("Could not update tenant schemas: %s", e)

    # 4. Seed default species if table is empty
    try:
        from app.models.animal import SpeciesRecord, DEFAULT_SPECIES
        db = _default_session_factory()
        if db.query(SpeciesRecord).count() == 0:
            for code, label, order in DEFAULT_SPECIES:
                db.add(SpeciesRecord(code=code, label=label, display_order=order))
            db.commit()
            logger.info("Seeded default species")
        db.close()
    except Exception as e:
        logger.warning("Could not seed species: %s", e)

    # 6. Background reminder scheduler (skipped under SQLite / tests).
    if settings.ENABLE_SCHEDULER and not settings.DATABASE_URL.startswith("sqlite"):
        try:
            from app.core.scheduler import start_scheduler
            start_scheduler()
        except Exception as e:
            logger.warning("Could not start reminder scheduler: %s", e)

    # 5. Seed initial admin user on first deployment (if no users exist)
    try:
        from app.models.user import User, UserRole
        db = _default_session_factory()
        if db.query(User).count() == 0:
            if settings.INITIAL_ADMIN_EMAIL and settings.INITIAL_ADMIN_PASSWORD:
                from app.core.pocketbase import pb_admin_token, pb_create_user
                try:
                    admin_token = pb_admin_token(
                        settings.POCKETBASE_URL,
                        settings.POCKETBASE_ADMIN_EMAIL,
                        settings.POCKETBASE_ADMIN_PASSWORD,
                    )
                    record = pb_create_user(
                        settings.POCKETBASE_URL,
                        admin_token,
                        email=settings.INITIAL_ADMIN_EMAIL,
                        password=settings.INITIAL_ADMIN_PASSWORD,
                        name=f"{settings.INITIAL_ADMIN_FIRST_NAME} {settings.INITIAL_ADMIN_LAST_NAME}".strip(),
                    )
                    admin = User(
                        pb_user_id=record["id"],
                        email=settings.INITIAL_ADMIN_EMAIL,
                        first_name=settings.INITIAL_ADMIN_FIRST_NAME,
                        last_name=settings.INITIAL_ADMIN_LAST_NAME,
                        role=UserRole.ADMIN,
                    )
                    db.add(admin)
                    db.commit()
                    logger.info("✅ Initial admin user created in PocketBase: %s", settings.INITIAL_ADMIN_EMAIL)
                except Exception as e:
                    logger.error("Failed to create initial admin in PocketBase: %s", e)
            else:
                logger.warning(
                    "⚠ Aucun utilisateur en base et INITIAL_ADMIN_EMAIL / "
                    "INITIAL_ADMIN_PASSWORD non définis. "
                    "Personne ne pourra se connecter."
                )
        db.close()
    except Exception as e:
        logger.warning("Could not seed initial admin: %s", e)

    # Warn loudly about missing PocketBase configuration (default tenant)
    missing = []
    if not settings.POCKETBASE_URL:
        missing.append("POCKETBASE_URL")
    if not settings.POCKETBASE_ADMIN_EMAIL:
        missing.append("POCKETBASE_ADMIN_EMAIL")
    if not settings.POCKETBASE_ADMIN_PASSWORD:
        missing.append("POCKETBASE_ADMIN_PASSWORD")
    if missing:
        logger.warning(
            "⚠ CONFIGURATION INCOMPLÈTE – Variables PocketBase manquantes : %s. "
            "La création d'utilisateurs et l'authentification risquent de ne pas fonctionner.",
            ", ".join(missing),
        )


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
