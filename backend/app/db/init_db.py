from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def init_db(db: AsyncSession) -> None:
    """Verify database connectivity without creating or inserting application data."""
    await db.execute(text("SELECT 1"))
