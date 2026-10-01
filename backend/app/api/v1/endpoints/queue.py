from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from app.services.queue_service import queue_service
from app.schemas.appointment import Appointment as AppointmentSchema
from app.api import deps
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User
from sqlalchemy import select

router = APIRouter()

@router.get("/status")
async def queue_status(
    doctor_id: int | None = None,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "doctor":
        doctor_result = await db.execute(select(Doctor).where(Doctor.user_id == current_user.id))
        doctor = doctor_result.scalars().first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found.")
        if doctor_id is not None and doctor_id != doctor.id:
            raise HTTPException(status_code=403, detail="You can only view your own queue.")
        doctor_id = doctor.id
    elif current_user.role not in {"nurse", "staff", "admin"}:
        raise HTTPException(status_code=403, detail="You are not authorized to view the clinical queue.")
    query = select(Appointment).where(
        Appointment.status.in_(["check_in", "treating"]),
        Appointment.queue_position > 0,
    ).order_by(Appointment.queue_position.asc())
    if doctor_id is not None:
        query = query.where(Appointment.doctor_id == doctor_id)
    result = await db.execute(query)
    appointments = result.scalars().all()
    return {
        "items": [
            {
                "id": item.id,
                "patient_id": item.patient_id,
                "doctor_id": item.doctor_id,
                "position": item.queue_position,
                "status": item.status,
                "priority": item.priority,
                "scheduled_time": item.scheduled_time,
            }
            for item in appointments
        ]
    }

@router.put("/complete/{appointment_id}", response_model=AppointmentSchema)
async def complete_queue_item(
    appointment_id: int,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {"doctor", "nurse", "staff", "admin"}:
        raise HTTPException(status_code=403, detail="You are not authorized to complete queue appointments.")
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Queue appointment not found.")
    if appointment.status not in {"check_in", "treating"} or appointment.queue_position <= 0:
        raise HTTPException(status_code=409, detail="Appointment is not an active queue entry.")
    if current_user.role == "doctor":
        doctor_result = await db.execute(select(Doctor).where(Doctor.user_id == current_user.id))
        doctor = doctor_result.scalars().first()
        if not doctor or appointment.doctor_id != doctor.id:
            raise HTTPException(status_code=403, detail="You can only complete your own queue appointments.")
    appointment.status = "completed"
    await db.commit()
    await db.refresh(appointment)
    return appointment

@router.post("/join/{appointment_id}", response_model=AppointmentSchema)
async def join_queue(
    appointment_id: int,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Patient check-in to join the live queue.
    """
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can check in to the queue.")
    patient_result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = patient_result.scalars().first()
    appointment_result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = appointment_result.scalar_one_or_none()
    if not appointment or appointment.status != "scheduled":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or not eligible for check-in."
        )
    if not patient or appointment.patient_id != patient.id:
        raise HTTPException(status_code=403, detail="You can only check in to your own appointment.")
    joined_appointment = await queue_service.join_queue(db, appointment_id)
    if not joined_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or not eligible for check-in."
        )
    return joined_appointment

@router.post("/next/{doctor_id}", response_model=AppointmentSchema)
async def call_next_patient(
    doctor_id: int,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Doctor calls the next patient in their queue.
    """
    doctor_result = await db.execute(select(Doctor).where(Doctor.user_id == current_user.id))
    doctor = doctor_result.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    if doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="You can only call patients from your own queue.")
    appointment = await queue_service.get_next_patient(db, doctor.id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patients in queue."
        )
    return appointment

@router.get("/wait-time/{doctor_id}")
async def get_estimated_wait(doctor_id: int, position: int, db: AsyncSession = Depends(get_db)):
    """
    Get estimated wait time for a position in the queue.
    """
    wait_time = await queue_service.calculate_wait_time(db, doctor_id, position)
    return {"estimated_wait_minutes": wait_time}
