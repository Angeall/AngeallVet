import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings

logger = logging.getLogger(__name__)
from app.core.database import Base, _default_engine as engine, _default_session_factory
from app.api.endpoints import (
    auth, clients, animals, appointments,
    medical, inventory, billing, communication, hospitalization,
)

app = FastAPI(
    title=settings.APP_NAME,
    description="Système de gestion pour cliniques vétérinaires (PMS)",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(clients.router, prefix=API_PREFIX)
app.include_router(animals.router, prefix=API_PREFIX)
app.include_router(appointments.router, prefix=API_PREFIX)
app.include_router(medical.router, prefix=API_PREFIX)
app.include_router(inventory.router, prefix=API_PREFIX)
app.include_router(billing.router, prefix=API_PREFIX)
app.include_router(communication.router, prefix=API_PREFIX)
app.include_router(hospitalization.router, prefix=API_PREFIX)

# Serve uploads
upload_dir = settings.UPLOAD_DIR
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


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
        conn.commit()


@app.on_event("startup")
def on_startup():
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

    # Warn loudly about missing Supabase configuration
    missing = []
    if not settings.SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not settings.SUPABASE_JWT_SECRET:
        missing.append("SUPABASE_JWT_SECRET")
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        logger.warning(
            "⚠ CONFIGURATION INCOMPLÈTE – Variables manquantes : %s. "
            "L'authentification ne fonctionnera PAS.",
            ", ".join(missing),
        )


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
