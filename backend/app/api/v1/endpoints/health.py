"""Liveness, dependency readiness, and administrator-only diagnostics."""

import logging
import platform
import time
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from app.api import deps
from app.core.config import settings
from app.core.metrics import WS_ACTIVE_CONNECTIONS
from app.db.session import SessionLocal, engine
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()
_STARTED_AT = time.monotonic()


async def _check_database() -> tuple[bool, str | None]:
    try:
        async with SessionLocal() as db:
            result = await db.execute(text("SELECT 1"))
            if result.scalar_one() != 1:
                raise RuntimeError("Database health query returned an unexpected result")
        return True, None
    except Exception:
        logger.exception("Readiness check could not reach PostgreSQL")
        return False, None


async def _check_redis() -> tuple[bool, dict[str, Any] | None]:
    redis = None
    try:
        redis = Redis.from_url(settings.REDIS_URL)
        await redis.ping()
        server_info = await redis.info("server")
        client_info = await redis.info("clients")
        return True, {**server_info, **client_info}
    except Exception:
        logger.exception("Readiness check could not reach Redis")
        return False, None
    finally:
        if redis is not None:
            await redis.aclose()


def _pool_stat(pool: Any, method: str) -> int | None:
    value = getattr(pool, method, None)
    return value() if callable(value) else None


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


@router.get("/health", tags=["system"])
async def liveness():
    """Confirm the process is running without probing external dependencies."""
    return {"status": "ok"}


@router.get("/ready", tags=["system"])
async def readiness():
    """Report readiness only when both the configured database and Redis respond."""
    database_ok, _ = await _check_database()
    redis_ok, _ = await _check_redis()
    dependencies = {
        "database": "reachable" if database_ok else "unreachable",
        "redis": "reachable" if redis_ok else "unreachable",
    }
    ready = database_ok and redis_ok
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "dependencies": dependencies},
    )


@router.get("/health/details", tags=["system"])
async def health_details(
    _admin: User = Depends(deps.check_role(["admin", "super_admin"])),
):
    """Return operational diagnostics to authenticated administrators only."""
    database_ok, _ = await _check_database()
    redis_ok, redis_info = await _check_redis()
    pool = engine.sync_engine.pool
    try:
        async with SessionLocal() as db:
            db_version = (await db.execute(text("SELECT version()"))).scalar_one()
    except Exception:
        db_version = None

    return {
        "versions": {
            "application": "1.0.0",
            "python": platform.python_version(),
            "fastapi": _package_version("fastapi"),
            "postgresql": db_version,
            "redis": (redis_info or {}).get("redis_version"),
        },
        "database": "reachable" if database_ok else "unreachable",
        "redis": {
            "status": "reachable" if redis_ok else "unreachable",
            "connected_clients": (redis_info or {}).get("connected_clients"),
        },
        "db_pool": {
            "pool_class": type(pool).__name__,
            "size": _pool_stat(pool, "size"),
            "checked_in": _pool_stat(pool, "checkedin"),
            "checked_out": _pool_stat(pool, "checkedout"),
            "overflow": _pool_stat(pool, "overflow"),
        },
        "websocket_active_connections": int(WS_ACTIVE_CONNECTIONS._value.get()),
        "uptime_seconds": round(time.monotonic() - _STARTED_AT, 3),
    }
