import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings

logger = logging.getLogger(__name__)
from app.core.database import engine, Base
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


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

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
