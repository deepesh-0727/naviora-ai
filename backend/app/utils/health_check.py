import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


async def check_database_health(db: AsyncSession) -> bool:
    try:
        result = await db.execute(select(1))
        return result.scalar() == 1
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        return False


async def check_redis_health() -> bool:
    redis = None
    try:
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        pong = await redis.ping()
        return pong is True
    except (RedisError, Exception) as exc:
        logger.error(f"Redis health check failed: {exc}")
        return False
    finally:
        if redis:
            await redis.aclose()


async def check_ai_service_health() -> bool:
    try:
        if settings.AI_PROVIDER.lower() == "openai":
            if not settings.OPENAI_API_KEY:
                return False
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                )
                return response.status_code == 200

        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/version")
            return response.status_code == 200
    except Exception:
        logger.exception("AI service health check failed")
        return False


async def get_system_health(db: AsyncSession):
    db_ok = await check_database_health(db)
    redis_ok = await check_redis_health()
    ai_ok = await check_ai_service_health()

    status = "healthy" if (db_ok and redis_ok) else "degraded"
    return {
        "status": status,
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
        "ai_service": "ok" if ai_ok else "degraded",
    }
