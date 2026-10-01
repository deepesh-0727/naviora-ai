import asyncio
import pytest
from typing import AsyncGenerator, Generator
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import String
from geoalchemy2 import Geometry

from app.main import app
from app.db.base_class import Base
from app.api.deps import get_db as deps_get_db
from app.db.session import get_db as session_get_db

# Use an in-memory SQLite database for fast unit testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# SQLite does not provide SpatiaLite's RecoverGeometryColumn function. Tests
# that use SQLite do not exercise spatial queries, so represent geometry as text.
for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, Geometry):
            column.type = String()

TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_engine():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[deps_get_db] = override_get_db
    app.dependency_overrides[session_get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
