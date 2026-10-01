from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.db.session import get_db
from app.services.analytics.analytics_service import analytics_service

router = APIRouter()

@router.get("/kpis")
async def get_hospital_kpis(db: AsyncSession = Depends(get_db)):
    """
    Get hospital-wide Key Performance Indicators.
    Access restricted to Admin users in production.
    """
    return await analytics_service.get_hospital_kpis(db)

@router.get("/reports")
async def get_operational_reports():
    return {"reports": ["Daily Admissions", "Average Wait Times", "Pharmacy Turnover"]}

@router.get("/audit-logs")
async def get_system_audit_logs(limit: int = 100):
    return {"logs": [{"timestamp": "2026-08-12 10:00", "action": "LOGIN", "user": "Dr. Sharma"}]}
