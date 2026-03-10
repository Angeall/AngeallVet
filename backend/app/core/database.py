from contextvars import ContextVar
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


# Default engine for the central database (tenants table, users table)
_default_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
_default_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=_default_engine)

# Cache of per-tenant engines keyed by database_url
_tenant_engines: dict[str, any] = {}
_tenant_session_factories: dict[str, sessionmaker] = {}

# Context variable: holds the tenant's database_url for the current request
_current_tenant_db_url: ContextVar[str | None] = ContextVar("current_tenant_db_url", default=None)


class Base(DeclarativeBase):
    pass


def set_tenant_db_url(db_url: str | None):
    """Set the tenant database URL for the current request context."""
    _current_tenant_db_url.set(db_url)


def get_tenant_db_url() -> str | None:
    """Get the tenant database URL from the request context."""
    return _current_tenant_db_url.get()


def _get_tenant_session_factory(db_url: str) -> sessionmaker:
    """Get or create a session factory for a tenant database URL (cached)."""
    if db_url not in _tenant_session_factories:
        engine = create_engine(db_url, pool_pre_ping=True)
        _tenant_engines[db_url] = engine
        _tenant_session_factories[db_url] = sessionmaker(
            autocommit=False, autoflush=False, bind=engine,
        )
    return _tenant_session_factories[db_url]


def get_db():
    """Yield a DB session for the current tenant, or the central DB if no tenant."""
    tenant_url = get_tenant_db_url()
    if tenant_url:
        factory = _get_tenant_session_factory(tenant_url)
    else:
        factory = _default_session_factory

    db = factory()
    try:
        yield db
    finally:
        db.close()


def get_central_db():
    """Always yield a session to the central database (for tenant/user lookups)."""
    db = _default_session_factory()
    try:
        yield db
    finally:
        db.close()


def init_tenant_database(db_url: str):
    """Create all tables in a tenant database (for provisioning new tenants)."""
    engine = create_engine(db_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    engine.dispose()
