import asyncio
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.db.session import get_db
from app.models.hospital import AuditLog
from app.models.user import User

router = APIRouter()
ADMIN_ROLES = ["admin", "super_admin"]


async def _probe(service: str, db: AsyncSession) -> dict[str, object]:
    if service == "database":
        started = perf_counter()
        await db.execute(text("SELECT 1"))
        return {"service": service, "reachable": True, "latency_ms": round((perf_counter() - started) * 1000, 2)}
    if service == "redis":
        client = Redis.from_url(settings.REDIS_URL)
        try:
            started = perf_counter()
            await client.ping()
            return {"service": service, "reachable": True, "latency_ms": round((perf_counter() - started) * 1000, 2)}
        finally:
            await client.aclose()
    if service == "rabbitmq":
        reader, writer = await asyncio.wait_for(asyncio.open_connection(settings.RABBITMQ_HOST, settings.RABBITMQ_PORT), timeout=3)
        writer.close()
        await writer.wait_closed()
        return {"service": service, "reachable": True}
    raise HTTPException(status_code=404, detail="Service is not configured for health checks.")


@router.get("/services")
async def service_health(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    results = []
    for service in ("database", "redis", "rabbitmq"):
        try:
            results.append(await _probe(service, db))
        except Exception:
            results.append({"service": service, "reachable": False})
    return {"items": results}


@router.get("/latency")
async def service_latency(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    values = []
    for service in ("database", "redis", "rabbitmq"):
        try:
            values.append(await _probe(service, db))
        except Exception:
            values.append({"service": service, "reachable": False})
    return {"items": values}


@router.get("/errors")
async def recent_errors(limit: int = 100, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    safe_limit = min(max(limit, 1), 1000)
    result = await db.execute(select(AuditLog).where(AuditLog.status.in_(["400", "401", "403", "404", "409", "422", "500", "503", "error", "failed"])).order_by(AuditLog.created_at.desc()).limit(safe_limit))
    return {"items": result.scalars().all()}


@router.post("/cache/clear")
async def clear_application_cache(current_user: User = Depends(deps.check_role(ADMIN_ROLES))):
    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        removed = 0
        async for key in client.scan_iter(match=f"{settings.CACHE_PREFIX}*"):
            removed += await client.delete(key)
        return {"deleted_cache_entries": removed}
    finally:
        await client.aclose()
