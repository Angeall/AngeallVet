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
    controlled_substances, associations,
)
from app.api.endpoints import settings as settings_endpoints

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
app.include_router(settings_endpoints.router, prefix=API_PREFIX)
app.include_router(controlled_substances.router, prefix=API_PREFIX)
app.include_router(associations.router, prefix=API_PREFIX)

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
        ("clients", "vat_number", "ALTER TABLE clients ADD COLUMN vat_number VARCHAR(50)"),
        ("products", "is_controlled_substance", "ALTER TABLE products ADD COLUMN is_controlled_substance BOOLEAN NOT NULL DEFAULT false"),
        ("animals", "association_id", "ALTER TABLE animals ADD COLUMN association_id INTEGER REFERENCES associations(id)"),
        ("reminder_rules", "postal_template", "ALTER TABLE reminder_rules ADD COLUMN postal_template TEXT"),
        ("medical_record_products", "treatment_location", "ALTER TABLE medical_record_products ADD COLUMN treatment_location VARCHAR(20) NOT NULL DEFAULT 'home'"),
        ("consultation_templates", "home_treatment", "ALTER TABLE consultation_templates ADD COLUMN home_treatment TEXT"),
        ("controlled_substance_entries", "dosage", "ALTER TABLE controlled_substance_entries ADD COLUMN dosage VARCHAR(200)"),
        ("controlled_substance_entries", "total_delivered", "ALTER TABLE controlled_substance_entries ADD COLUMN total_delivered NUMERIC(10,2)"),
        ("users", "sidenav_color", "ALTER TABLE users ADD COLUMN sidenav_color VARCHAR(7)"),
        ("invoices", "medical_record_id", "ALTER TABLE invoices ADD COLUMN medical_record_id INTEGER REFERENCES medical_records(id)"),
        ("invoice_lines", "lot_number", "ALTER TABLE invoice_lines ADD COLUMN lot_number VARCHAR(100)"),
        ("medical_record_products", "lot_number", "ALTER TABLE medical_record_products ADD COLUMN lot_number VARCHAR(100)"),
        ("medical_records", "pharmacy_prescription", "ALTER TABLE medical_records ADD COLUMN pharmacy_prescription TEXT"),
        ("medical_records", "context", "ALTER TABLE medical_records ADD COLUMN context TEXT"),
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

    # 5. Seed initial admin user on first deployment (if no users exist)
    try:
        from app.models.user import User, UserRole
        db = _default_session_factory()
        if db.query(User).count() == 0:
            if settings.INITIAL_ADMIN_EMAIL and settings.INITIAL_ADMIN_PASSWORD:
                from app.core.supabase import get_supabase_admin
                supabase = get_supabase_admin()
                try:
                    auth_response = supabase.auth.admin.create_user({
                        "email": settings.INITIAL_ADMIN_EMAIL,
                        "password": settings.INITIAL_ADMIN_PASSWORD,
                        "email_confirm": True,
                        "user_metadata": {
                            "first_name": settings.INITIAL_ADMIN_FIRST_NAME,
                            "last_name": settings.INITIAL_ADMIN_LAST_NAME,
                            "role": "admin",
                        },
                    })
                    admin = User(
                        supabase_uid=auth_response.user.id,
                        email=settings.INITIAL_ADMIN_EMAIL,
                        first_name=settings.INITIAL_ADMIN_FIRST_NAME,
                        last_name=settings.INITIAL_ADMIN_LAST_NAME,
                        role=UserRole.ADMIN,
                    )
                    db.add(admin)
                    db.commit()
                    logger.info("✅ Initial admin user created: %s", settings.INITIAL_ADMIN_EMAIL)
                except Exception as e:
                    logger.error("Failed to create initial admin in Supabase: %s", e)
            else:
                logger.warning(
                    "⚠ Aucun utilisateur en base et INITIAL_ADMIN_EMAIL / "
                    "INITIAL_ADMIN_PASSWORD non définis. "
                    "Personne ne pourra se connecter."
                )
        db.close()
    except Exception as e:
        logger.warning("Could not seed initial admin: %s", e)

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
