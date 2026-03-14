import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# Set DATABASE_URL to SQLite BEFORE any app imports, so database.py
# creates an in-memory engine instead of trying to connect to PostgreSQL.
os.environ["DATABASE_URL"] = "sqlite://"

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db, get_central_db
from app.api.deps import get_tenant_db
from app.main import app
from app.models.user import User, UserRole


# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"
TEST_JWT_SECRET = "test-supabase-jwt-secret"

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


def _create_test_token(supabase_uid: str) -> str:
    """Create a fake Supabase-style JWT for testing."""
    payload = {
        "sub": supabase_uid,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def mock_supabase_jwt_secret():
    """Override the Supabase JWT secret for testing."""
    with patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET):
        yield


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

    def override_get_central_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_central_db] = override_get_central_db
    app.dependency_overrides[get_tenant_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    uid = str(uuid.uuid4())
    user = User(
        supabase_uid=uid,
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
    uid = str(uuid.uuid4())
    user = User(
        supabase_uid=uid,
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
    return _create_test_token(admin_user.supabase_uid)


@pytest.fixture
def vet_token(vet_user):
    return _create_test_token(vet_user.supabase_uid)


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def vet_headers(vet_token):
    return {"Authorization": f"Bearer {vet_token}"}
