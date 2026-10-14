import hashlib
import json
import logging
from typing import Dict, Any, Optional
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    def _hash_query(self, query: str) -> str:
        cleaned = query.strip().lower()
        return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

    def _get_key(self, query: str, scope: str) -> str:
        scope_hash = hashlib.sha256(scope.encode("utf-8")).hexdigest()
        return f"{settings.CACHE_PREFIX}{scope_hash}:{self._hash_query(query)}"

    async def get_cached_intent(self, query: str, scope: str = "global") -> Optional[Dict[str, Any]]:
        if not settings.CACHE_ENABLED:
            return None

        redis = None
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            cached_val = await redis.get(self._get_key(query, scope))
            if cached_val:
                logger.info(f"Cache hit for query: '{query}'")
                return json.loads(cached_val)
        except (RedisError, Exception) as exc:
            logger.warning(f"Redis cache read error: {exc}")
        finally:
            if redis:
                await redis.aclose()
        return None

    async def set_cached_intent(self, query: str, result: Dict[str, Any], ttl: Optional[int] = None, scope: str = "global") -> bool:
        if not settings.CACHE_ENABLED:
            return False

        redis = None
        expiry = ttl if ttl is not None else settings.CACHE_TTL
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            key = self._get_key(query, scope)
            val_str = json.dumps(result)
            await redis.set(key, val_str, ex=expiry)
            logger.info(f"Cached intent result for query: '{query}' with TTL: {expiry}s")
            return True
        except (RedisError, Exception) as exc:
            logger.warning(f"Redis cache write error: {exc}")
            return False
        finally:
            if redis:
                await redis.aclose()

    async def invalidate_cache(self, query: str, scope: str = "global") -> bool:
        redis = None
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            await redis.delete(self._get_key(query, scope))
            return True
        except (RedisError, Exception) as exc:
            logger.warning(f"Redis cache invalidation error: {exc}")
            return False
        finally:
            if redis:
                await redis.aclose()


cache_service = CacheService()
