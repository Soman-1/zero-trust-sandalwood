"""Pytest configuration and shared fixtures with isolated test database."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.core.runtime as runtime
from app.database.base import Base
from app.database.database import get_db
from app.core.config import settings
from app.main import create_app

# Use in-memory SQLite database with StaticPool for test isolation
TEST_DATABASE_URL = "sqlite:///:memory:"
settings.ENV_REFRESH_ENABLED = False
settings.ALLOW_INSECURE_DEFAULTS = True
settings.ALLOW_PUBLIC_REGISTRATION = True
if not (settings.JWT_SECRET or "").strip():
    settings.JWT_SECRET = "test-jwt-secret-key-at-least-32-characters-long"
if not (settings.ENCRYPTION_KEY or "").strip():
    settings.ENCRYPTION_KEY = "test-encryption-key-at-least-32-characters-ok"
# Existing tests create privileged users through /auth/register.
# Production leaves this False; public registration stays viewer-only.
runtime.privileged_self_register = True
runtime.require_ingest_freshness = False
runtime.exempt_testclient_rate_limit = True

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

import app.database.database as db_mod
import app.main as main_mod
db_mod.SessionLocal = TestingSessionLocal
db_mod.engine = test_engine
# main.lifespan imported SessionLocal by name; keep it on the test engine
main_mod.SessionLocal = TestingSessionLocal


@pytest.fixture(scope="session")
def app():
    """Application fixture."""
    return create_app()


@pytest.fixture(scope="function")
def db_session():
    """Create fresh database tables for each test function."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(app, db_session):
    """Test client fixture with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_headers(client, username: str, role: str = "ADMIN") -> dict:
    """Register a unique user and return Authorization headers."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{username}@agroforestry.gov.in",
            "username": username,
            "full_name": f"{username} User",
            "password": "Password12345!",
            "role": role,
        },
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username, "password": "Password12345!"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
