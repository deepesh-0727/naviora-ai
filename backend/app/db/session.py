from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Pool arguments are only valid for PostgreSQL/asyncpg.
# SQLite (used in CI / unit tests) does not support them.
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {"echo": False}

if not _is_sqlite:
    # Enterprise Engine Configuration for Supabase / PostgreSQL.
    # pool_pre_ping: Verifies the connection is alive (crucial for cloud DBs).
    # pool_size / max_overflow: Tuned for Supabase Free Tier connection limits.
    _engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
    )

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """
    Dependency injection for FastAPI.
    Ensures safe session handling and transaction rollback on failure.
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
