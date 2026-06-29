import os
import uuid

# Set DATABASE_URL to SQLite BEFORE any app imports, so database.py
# creates an in-memory engine instead of trying to connect to PostgreSQL.
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db, get_central_db, get_request_db
from app.core.security import create_app_token
from app.core.tenancy import derive_tenant_secret
from app.api.deps import get_tenant_db
from app.main import app
from app.models.user import User, UserRole


# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# Enable foreign key support in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _create_test_token(pb_user_id: str) -> str:
    """Mint an application JWT for the default tenant, exactly as the backend
    would after a successful PocketBase token exchange."""
    return create_app_token(pb_user_id, derive_tenant_secret(settings.DEFAULT_TENANT_SLUG))


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    # All DB providers resolve to the single in-memory test session. The real
    # auth path (get_current_user -> verify app JWT -> load user) still runs.
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_central_db] = override_get_db
    app.dependency_overrides[get_request_db] = override_get_db
    app.dependency_overrides[get_tenant_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    user = User(
        pb_user_id=str(uuid.uuid4()),
        email="admin@test.com",
        first_name="Admin",
        last_name="Test",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def vet_user(db):
    user = User(
        pb_user_id=str(uuid.uuid4()),
        email="vet@test.com",
        first_name="Dr",
        last_name="Vet",
        role=UserRole.VETERINARIAN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    return _create_test_token(admin_user.pb_user_id)


@pytest.fixture
def vet_token(vet_user):
    return _create_test_token(vet_user.pb_user_id)


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def vet_headers(vet_token):
    return {"Authorization": f"Bearer {vet_token}"}
