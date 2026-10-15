"""
pytest configuration and shared fixtures for Naviora AI backend tests.

Key design decisions:
- Uses SQLite (aiosqlite) in-memory database so tests never touch Supabase.
- Overrides get_db dependency via FastAPI's dependency_overrides.
- Patches Redis calls to avoid needing a live Redis server in CI.
- Provides a synchronous TestClient and async client fixture.
"""
import os
from unittest.mock import AsyncMock
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

pytest_plugins = ("integration_fixtures",)

# ── Force environment to test values BEFORE importing the app ──────────────
os.environ["SECRET_KEY"] = "test-secret-key-naviora-ci-only-32"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = os.getenv("NAVIORA_TEST_REDIS_URL", "redis://localhost:6379/0")
os.environ["TEXTLOCAL_API_KEY"] = ""
os.environ["EMAIL_API_KEY"] = ""
os.environ["FIREBASE_CREDENTIALS"] = ""
os.environ["RAZORPAY_KEY_ID"] = ""
os.environ["RAZORPAY_KEY_SECRET"] = ""
os.environ["SENTRY_DSN"] = ""

from app.main import app                          # noqa: E402 — env must be set first
from app.db.session import get_db                 # noqa: E402
from app.api.deps import get_db as dependency_get_db  # noqa: E402
from app.db.base import Base                      # noqa: E402  (SQLAlchemy declarative base)
from app.services.ws_manager import ws_manager    # noqa: E402

# ---------------------------------------------------------------------------
# In-memory SQLite engine (single connection, shared across the test session)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_engine.sync_engine, "connect")
def _register_sqlite_geometry_binding(dbapi_connection, connection_record):
    """Support NULL geometry values without requiring SpatiaLite in unit tests."""
    dbapi_connection.create_function("GeomFromEWKT", 1, lambda value: None)
    dbapi_connection.create_function("ST_AsEWKB", 1, lambda value: value)

_TestingSessionLocal = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)
app.state.rbac_session_factory = _TestingSessionLocal
app.state.audit_session_factory = _TestingSessionLocal


@pytest.fixture(autouse=True)
def disable_global_websocket_lifecycle(monkeypatch):
    """Avoid requiring an external Redis server in API tests; manager tests inject their own broker."""
    monkeypatch.setattr(ws_manager, "start", AsyncMock())
    monkeypatch.setattr(ws_manager, "shutdown", AsyncMock())


# ---------------------------------------------------------------------------
# Per-test table lifecycle keeps the async SQLite engine on the same event loop.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def create_tables():
    """Create service tables in the isolated SQLite database for each test."""
    from app.models.appointment import Appointment
    from app.models.doctor import Doctor
    from app.models.emergency import EmergencyCase
    from app.models.user import User
    from app.models.hospital import AuditLog, StaffSchedule
    from app.models.operations import EmergencyMessage
    from app.models.patient import Patient
    from app.models.queue import QueueEntry
    from app.models.security import RefreshToken
    from app.models.pharmacy import Prescription
    from app.models.vitals import PatientVitals
    from app.models.billing import Billing

    async with _engine.begin() as conn:
        test_tables = [
            User.__table__, AuditLog.__table__, Patient.__table__,
            Doctor.__table__, Appointment.__table__, QueueEntry.__table__,
            StaffSchedule.__table__, RefreshToken.__table__, EmergencyMessage.__table__,
            Prescription.__table__, PatientVitals.__table__,
            Billing.__table__,
        ]
        # SQLite has no SpatiaLite extension in the test runtime. Keep the
        # ordinary department fields used by these tests, without a geometry
        # column that would require extension functions.
        await conn.exec_driver_sql(
            "CREATE TABLE departments ("
            "id INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL UNIQUE, "
            "description TEXT, floor INTEGER NOT NULL, building VARCHAR(50) NOT NULL, "
            "wing VARCHAR(50) NOT NULL, location BLOB, phone VARCHAR(20) NOT NULL, "
            "email VARCHAR(100) NOT NULL, created_at DATETIME)"
        )
        await conn.exec_driver_sql(
            "CREATE TABLE emergency_cases ("
            "id INTEGER PRIMARY KEY, patient_id INTEGER, status VARCHAR(20) NOT NULL, "
            "priority VARCHAR(20) NOT NULL, location_desc VARCHAR(255) NOT NULL, "
            "location_coords BLOB, description TEXT, assigned_staff JSON, "
            "ambulance_id VARCHAR(50), response_time INTEGER, acknowledged_at DATETIME, "
            "en_route_at DATETIME, arrival_time DATETIME, treatment_notes TEXT, "
            "created_at DATETIME, updated_at DATETIME)"
        )
        await conn.exec_driver_sql(
            "CREATE TABLE location_tracking ("
            "id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, latitude FLOAT NOT NULL, "
            "longitude FLOAT NOT NULL, accuracy FLOAT NOT NULL DEFAULT 1.0, floor INTEGER NOT NULL DEFAULT 0, "
            "building VARCHAR(50) NOT NULL DEFAULT 'Main', is_active BOOLEAN NOT NULL DEFAULT 1, "
            "created_at DATETIME, location BLOB)"
        )
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=test_tables))
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.drop_all(sync_conn, tables=test_tables))
        await conn.exec_driver_sql("DROP TABLE IF EXISTS emergency_cases")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS location_tracking")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS departments")


# ---------------------------------------------------------------------------
# Per-test DB session (each test rolls back on teardown)
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def db_session(create_tables) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean AsyncSession for each test, rolled back after."""
    async with _TestingSessionLocal() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Override FastAPI's get_db dependency to use the test session
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def override_get_db(db_session: AsyncSession):
    """Globally replace get_db with the in-memory test session."""
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[dependency_get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(dependency_get_db, None)


# ---------------------------------------------------------------------------
# Synchronous TestClient (for most unit tests)
# ---------------------------------------------------------------------------
@pytest.fixture()
def client() -> TestClient:
    """Return a synchronous TestClient without opening production-service lifespan connections."""
    # Requests use the isolated SQLite dependency override below. Entering the
    # TestClient context would also run the app's production startup hook and
    # try to initialize the configured service database for every test.
    return TestClient(app, base_url="http://localhost", raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Async TestClient (for tests that need await)
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Return an async HTTPX client connected to the test app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
    ) as ac:
        yield ac
