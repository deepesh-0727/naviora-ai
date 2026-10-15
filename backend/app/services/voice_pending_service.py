"""Short-lived Redis state for explicit voice appointment confirmations."""

import json
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings


class VoicePendingService:
    TTL_SECONDS = 120
    KEY_PREFIX = "voice_pending:"
    _POP_SCRIPT = """
    local value = redis.call('GET', KEYS[1])
    if value then redis.call('DEL', KEYS[1]) end
    return value
    """

    @classmethod
    def key(cls, user_id: int) -> str:
        return f"{cls.KEY_PREFIX}{user_id}"

    @classmethod
    def resolution_key(cls, user_id: int) -> str:
        return f"voice_resolution:{user_id}"

    async def _with_redis(self, operation):
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            return await operation(redis)
        finally:
            await redis.aclose()

    async def set_pending(self, user_id: int, proposal: dict[str, Any]) -> None:
        payload = json.dumps(proposal, separators=(",", ":"))
        await self._with_redis(lambda redis: redis.set(self.key(user_id), payload, ex=self.TTL_SECONDS))

    async def get_pending(self, user_id: int) -> dict[str, Any] | None:
        async def read(redis):
            stored = await redis.get(self.key(user_id))
            if stored is None:
                return None
            try:
                proposal = json.loads(stored)
            except (TypeError, json.JSONDecodeError):
                await redis.delete(self.key(user_id))
                return None
            if not isinstance(proposal, dict):
                await redis.delete(self.key(user_id))
                return None
            return proposal

        return await self._with_redis(read)

    async def pop_pending(self, user_id: int) -> dict[str, Any] | None:
        async def pop(redis):
            stored = await redis.eval(self._POP_SCRIPT, 1, self.key(user_id))
            if stored is None:
                return None
            try:
                proposal = json.loads(stored)
            except (TypeError, json.JSONDecodeError):
                return None
            return proposal if isinstance(proposal, dict) else None

        return await self._with_redis(pop)

    async def clear_pending(self, user_id: int) -> None:
        await self._with_redis(lambda redis: redis.delete(self.key(user_id)))

    async def set_resolution(self, user_id: int, context: dict[str, Any]) -> None:
        payload = json.dumps(context, separators=(",", ":"))
        await self._with_redis(
            lambda redis: redis.set(self.resolution_key(user_id), payload, ex=self.TTL_SECONDS)
        )

    async def get_resolution(self, user_id: int) -> dict[str, Any] | None:
        async def read(redis):
            stored = await redis.get(self.resolution_key(user_id))
            if stored is None:
                return None
            try:
                context = json.loads(stored)
            except (TypeError, json.JSONDecodeError):
                await redis.delete(self.resolution_key(user_id))
                return None
            return context if isinstance(context, dict) else None

        return await self._with_redis(read)

    async def clear_resolution(self, user_id: int) -> None:
        await self._with_redis(lambda redis: redis.delete(self.resolution_key(user_id)))


voice_pending_service = VoicePendingService()
