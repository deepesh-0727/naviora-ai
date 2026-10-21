from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.emergency import EmergencyCase
from app.models.hospital import AuditLog
from app.models.patient import Patient
from app.models.user import User
from app.services.analytics.analytics_service import analytics_service

router = APIRouter()
ADMIN_ROLES = ["admin", "super_admin"]


@router.get("/kpis")
async def dashboard_kpis(
    current_user: User = Depends(deps.check_role(ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    base = await analytics_service.get_hospital_kpis(db)
    patients = await db.scalar(select(func.count(Patient.id)))
    users = await db.scalar(select(func.count(User.id)))
    appointments = await db.scalar(select(func.count(Appointment.id)))
    emergencies = await db.scalar(select(func.count(EmergencyCase.id)))
    staff = await db.scalar(select(func.count(User.id)).where(User.role.notin_(["patient", "admin", "super_admin"]), User.is_active.is_(True)))
    return {
        **base,
        "users_total": users or 0,
        "patients_total": patients or 0,
        "active_staff": staff or 0,
        "appointments_total": appointments or 0,
        "emergencies_total": emergencies or 0,
    }


@router.get("/charts")
async def dashboard_charts(
    days: int = 30,
    current_user: User = Depends(deps.check_role(ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    start = datetime.utcnow() - timedelta(days=min(max(days, 1), 365))
    result = await db.execute(
        select(func.date(Appointment.created_at), Appointment.status, func.count(Appointment.id))
        .where(Appointment.created_at >= start)
        .group_by(func.date(Appointment.created_at), Appointment.status)
        .order_by(func.date(Appointment.created_at))
    )
    return {"appointments_by_day_and_status": [
        {"date": str(day), "status": status, "count": count}
        for day, status, count in result.all()
    ]}


@router.get("/alerts")
async def dashboard_alerts(
    current_user: User = Depends(deps.check_role(ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    emergencies = await db.execute(select(EmergencyCase).where(EmergencyCase.status != "resolved").order_by(EmergencyCase.created_at))
    failed = await db.execute(select(AuditLog).where(AuditLog.status.in_(["401", "403", "failed", "error"])).order_by(AuditLog.created_at.desc()).limit(50))
    return {
        "active_emergencies": [{"id": item.id, "status": item.status, "priority": item.priority, "created_at": item.created_at} for item in emergencies.scalars().all()],
        "recent_access_denials": [{"id": item.id, "action": item.action, "resource": item.resource, "status": item.status, "created_at": item.created_at} for item in failed.scalars().all()],
    }
