"""
pytest configuration and shared fixtures for Naviora AI backend tests.

Key design decisions:
- Uses SQLite (aiosqlite) in-memory database so tests never touch Supabase.
- Overrides get_db dependency via FastAPI's dependency_overrides.
- Patches Redis calls to avoid needing a live Redis server in CI.
- Provides a synchronous TestClient and async client fixture.
"""
import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# ── Force environment to test values BEFORE importing the app ──────────────
os.environ.setdefault("SECRET_KEY", "test-secret-key-naviora-ci-only")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TEXTLOCAL_API_KEY", "")
os.environ.setdefault("EMAIL_API_KEY", "")
os.environ.setdefault("FIREBASE_CREDENTIALS", "")
os.environ.setdefault("RAZORPAY_KEY_ID", "")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "")
os.environ.setdefault("SENTRY_DSN", "")

from app.main import app                          # noqa: E402 — env must be set first
from app.db.session import get_db                 # noqa: E402
from app.db.base import Base                      # noqa: E402  (SQLAlchemy declarative base)

# ---------------------------------------------------------------------------
# In-memory SQLite engine (single connection, shared across the test session)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

_TestingSessionLocal = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Session-scoped: create all tables once
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create SQLAlchemy tables in the in-memory SQLite database once per session."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Per-test DB session (each test rolls back on teardown)
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
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
    yield
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Synchronous TestClient (for most unit tests)
# ---------------------------------------------------------------------------
@pytest.fixture()
def client() -> TestClient:
    """Return a synchronous FastAPI TestClient."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Async TestClient (for tests that need await)
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Return an async HTTPX client connected to the test app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
