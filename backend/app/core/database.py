from contextvars import ContextVar
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Context variable to carry tenant_id across the request lifecycle
_current_tenant_id: ContextVar[int | None] = ContextVar("current_tenant_id", default=None)


class Base(DeclarativeBase):
    pass


def set_tenant_id(tenant_id: int | None):
    """Set the current tenant_id for the request context."""
    _current_tenant_id.set(tenant_id)


def get_tenant_id() -> int | None:
    """Get the current tenant_id from the request context."""
    return _current_tenant_id.get()


def get_db():
    db = SessionLocal()
    try:
        # Set PostgreSQL session variable for RLS policies
        tenant_id = get_tenant_id()
        if tenant_id is not None:
            db.execute(text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)})
        yield db
    finally:
        db.close()
