from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.hospital import AuditLog
from app.models.user import User
from app.services.analytics.analytics_service import analytics_service

router = APIRouter()

@router.get("/kpis")
async def get_hospital_kpis(
    current_user: User = Depends(deps.check_role(["admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get hospital-wide Key Performance Indicators.
    Access restricted to Admin users in production.
    """
    return await analytics_service.get_hospital_kpis(db)

@router.get("/reports")
async def get_operational_reports(db: AsyncSession = Depends(get_db)):
    """Return report datasets derived from persisted operational records."""
    from app.models.appointment import Appointment
    from app.models.operations import Admission

    admissions = await db.execute(select(Admission.status, func.count(Admission.id)).group_by(Admission.status))
    appointments = await db.execute(select(Appointment.status, func.count(Appointment.id)).group_by(Appointment.status))
    return {
        "admissions_by_status": [{"status": status, "count": count} for status, count in admissions.all()],
        "appointments_by_status": [{"status": status, "count": count} for status, count in appointments.all()],
    }

@router.get("/audit-logs")
async def get_system_audit_logs(
    limit: int = 100,
    current_user: User = Depends(deps.check_role(["admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(max(limit, 1), 1000))
    )
    return {"logs": result.scalars().all()}
