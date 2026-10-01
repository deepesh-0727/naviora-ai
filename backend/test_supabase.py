import asyncio
from sqlalchemy import text
from app.db.session import engine


async def main():
    print("Testing async DB connection...")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 AS ok"))
            print("✅ Async DB connection works:", result.scalar())
    except Exception as e:
        print("❌ DB connection failed:", str(e))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())