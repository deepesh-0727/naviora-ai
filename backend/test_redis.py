import asyncio
from app.core.config import settings
import redis.asyncio as aioredis


async def test():
    print(f"Redis URL: {settings.REDIS_URL[:50]}...")
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        pong = await r.ping()
        print(f"✅ Redis PING: {pong}")

        await r.set("naviora:test", "hello", ex=60)
        val = await r.get("naviora:test")
        print(f"✅ Redis SET/GET: {val}")

        await r.delete("naviora:test")
        await r.close()
        print("✅ Redis working end-to-end")
    except Exception as e:
        print(f"❌ Redis failed: {type(e).__name__}: {e}")


asyncio.run(test())