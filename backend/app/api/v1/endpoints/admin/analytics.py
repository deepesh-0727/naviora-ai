import csv
from datetime import datetime, timedelta
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.communication import ConversationHistory
from app.models.doctor import Department, Doctor
from app.models.emergency import EmergencyCase
from app.models.user import User

router = APIRouter()
ADMIN_ROLES = ["admin", "super_admin"]


@router.get("/flow")
async def appointment_flow(days: int = 30, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    start = datetime.utcnow() - timedelta(days=min(max(days, 1), 365))
    result = await db.execute(select(Department.name, Appointment.status, func.count(Appointment.id)).join(Department, Department.id == Appointment.department_id).where(Appointment.created_at >= start).group_by(Department.name, Appointment.status).order_by(Department.name, Appointment.status))
    return {"items": [{"department": name, "status": status, "count": count} for name, status, count in result.all()]}


@router.get("/wait-times")
async def wait_times(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Appointment.doctor_id, func.avg(Appointment.wait_time_minutes), func.count(Appointment.id)).where(Appointment.status == "completed").group_by(Appointment.doctor_id).order_by(Appointment.doctor_id))
    return {"items": [{"doctor_id": doctor_id, "average_wait_minutes": round(float(avg or 0), 2), "completed_visits": count} for doctor_id, avg, count in result.all()]}


@router.get("/emergency")
async def emergency_analytics(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmergencyCase.status, func.count(EmergencyCase.id), func.avg(EmergencyCase.response_time)).group_by(EmergencyCase.status).order_by(EmergencyCase.status))
    return {"items": [{"status": status, "case_count": count, "average_response_seconds": round(float(avg), 2) if avg is not None else None} for status, count, avg in result.all()]}


@router.get("/no-shows")
async def no_shows(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Appointment.doctor_id, func.count(Appointment.id)).where(Appointment.status == "no_show").group_by(Appointment.doctor_id).order_by(Appointment.doctor_id))
    return {"items": [{"doctor_id": doctor_id, "no_show_count": count} for doctor_id, count in result.all()]}


@router.get("/doctor-productivity")
async def doctor_productivity(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Doctor.id, Doctor.first_name, Doctor.last_name, func.count(Appointment.id)).outerjoin(Appointment, (Appointment.doctor_id == Doctor.id) & (Appointment.status == "completed")).group_by(Doctor.id, Doctor.first_name, Doctor.last_name).order_by(Doctor.last_name, Doctor.first_name))
    return {"items": [{"doctor_id": doctor_id, "doctor_name": f"{first_name} {last_name}", "completed_appointments": count} for doctor_id, first_name, last_name, count in result.all()]}


@router.get("/voice")
async def voice_analytics(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ConversationHistory.intent, ConversationHistory.agent_used, func.count(ConversationHistory.id)).group_by(ConversationHistory.intent, ConversationHistory.agent_used).order_by(ConversationHistory.intent, ConversationHistory.agent_used))
    return {"items": [{"intent": intent, "agent": agent, "request_count": count} for intent, agent, count in result.all()]}


@router.get("/export")
async def export_analytics(
    dataset: str = "flow",
    current_user: User = Depends(deps.check_role(ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    output = StringIO()
    writer = csv.writer(output)
    if dataset == "flow":
        result = await db.execute(select(Appointment.id, Appointment.patient_id, Appointment.doctor_id, Appointment.department_id, Appointment.status, Appointment.created_at).order_by(Appointment.created_at.desc()).limit(10000))
        writer.writerow(["appointment_id", "patient_id", "doctor_id", "department_id", "status", "created_at"])
        writer.writerows(result.all())
    elif dataset == "emergency":
        result = await db.execute(select(EmergencyCase.id, EmergencyCase.status, EmergencyCase.priority, EmergencyCase.response_time, EmergencyCase.created_at).order_by(EmergencyCase.created_at.desc()).limit(10000))
        writer.writerow(["emergency_id", "status", "priority", "response_time_seconds", "created_at"])
        writer.writerows(result.all())
    else:
        raise HTTPException(status_code=422, detail="Supported export datasets are flow and emergency.")
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=naviora-{dataset}-analytics.csv"})
