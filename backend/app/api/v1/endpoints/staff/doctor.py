from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.pharmacy import Prescription
from app.models.operations import LabOrder
from app.models.user import User

router = APIRouter()


async def _doctor_id(db: AsyncSession, user: User) -> int:
    result = await db.execute(select(Doctor.id).where(Doctor.user_id == user.id))
    doctor_id = result.scalar_one_or_none()
    if doctor_id is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    return doctor_id


@router.get("/schedule")
async def schedule(
    schedule_date: str | None = Query(default=None, alias="date"),
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    doctor_id = await _doctor_id(db, current_user)
    if schedule_date is None or schedule_date.lower() == "today":
        target_date = date.today()
    else:
        try:
            target_date = date.fromisoformat(schedule_date)
        except ValueError as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="date must be 'today' or an ISO date (YYYY-MM-DD).") from exc
    start = datetime.combine(target_date, time.min)
    end = start + timedelta(days=1)
    result = await db.execute(
        select(Appointment, Patient.first_name, Patient.last_name)
        .join(Patient, Patient.id == Appointment.patient_id)
        .where(Appointment.doctor_id == doctor_id, Appointment.scheduled_time >= start, Appointment.scheduled_time < end)
        .order_by(Appointment.scheduled_time)
    )
    return [{
        "id": appointment.id,
        "patient_id": appointment.patient_id,
        "patient_name": f"{first_name} {last_name}",
        "scheduled_time": appointment.scheduled_time,
        "status": appointment.status,
        "priority": appointment.priority,
    } for appointment, first_name, last_name in result.all()]


@router.get("/queue")
async def doctor_queue(
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    doctor_id = await _doctor_id(db, current_user)
    result = await db.execute(
        select(Appointment, Patient.first_name, Patient.last_name)
        .join(Patient, Patient.id == Appointment.patient_id)
        .where(Appointment.doctor_id == doctor_id, Appointment.status.in_(["check_in", "treating"]))
        .order_by(Appointment.queue_position, Appointment.scheduled_time)
    )
    return {"items": [{
        "id": appointment.id,
        "appointment_id": appointment.id,
        "patient_id": appointment.patient_id,
        "patient_name": f"{first_name} {last_name}",
        "doctor_id": doctor_id,
        "position": appointment.queue_position,
        "status": appointment.status,
        "priority": appointment.priority,
        "scheduled_time": appointment.scheduled_time,
    } for appointment, first_name, last_name in result.all()]}


@router.get("/stats/today")
async def doctor_today_stats(
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    doctor_id = await _doctor_id(db, current_user)
    start = datetime.combine(date.today(), time.min)
    end = start + timedelta(days=1)
    result = await db.execute(
        select(Appointment.status, func.count(Appointment.id))
        .where(Appointment.doctor_id == doctor_id, Appointment.scheduled_time >= start, Appointment.scheduled_time < end)
        .group_by(Appointment.status)
    )
    counts = {status: count for status, count in result.all()}
    pending_prescriptions = await db.scalar(
        select(func.count(Prescription.id)).where(Prescription.doctor_id == doctor_id, Prescription.status == "pending")
    )
    return {
        "total_patients": sum(counts.values()),
        "completed": counts.get("completed", 0),
        "waiting": counts.get("check_in", 0),
        "pending_prescriptions": pending_prescriptions or 0,
    }


@router.get("/prescriptions/pending")
async def pending_prescriptions(
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    doctor_id = await _doctor_id(db, current_user)
    result = await db.execute(select(Prescription).where(Prescription.doctor_id == doctor_id, Prescription.status == "pending").order_by(Prescription.created_at))
    return {"items": result.scalars().all()}


@router.get("/labs/pending")
async def pending_labs(
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LabOrder).where(LabOrder.ordered_by_id == current_user.id, LabOrder.status.in_(["pending", "in_progress"])).order_by(LabOrder.created_at))
    return {"items": result.scalars().all()}
