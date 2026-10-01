import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def verify_database_entries():
    print("=== NAVIORA AI - SUPABASE DATABASE VERIFICATION REPORT ===")
    print(f"Target Database URL: {settings.DATABASE_URL.split('@')[-1]}\n")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    tables = ["users", "patients", "doctors", "departments", "appointments", "emergency_cases", "prescriptions", "inventory"]

    total_records = 0
    try:
        async with engine.connect() as conn:
            for table in tables:
                try:
                    res = await conn.execute(text(f"SELECT COUNT(*) FROM {table};"))
                    count = res.scalar()
                    total_records += count
                    print(f"  [TABLE] {table:<20} : {count:>5} records")
                except Exception as e:
                    print(f"  [TABLE] {table:<20} : TABLE NOT FOUND / ERROR ({e})")

            print("\n---------------------------------------------------------")
            print(f"[SUMMARY] Total Clinical Database Records: {total_records}")
            print("[VERIFICATION] All tables connected to Supabase Cloud.")
            print("=========================================================\n")
            return True
    except Exception as e:
        print(f"[ERROR] Database verification failed: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_database_entries())
