from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from typing import List, Optional
from datetime import date, datetime, time, timezone
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_

from app.api import deps
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.doctor import Doctor, Department
from app.services.availability_service import database_datetime, get_available_slots
from app.core.rate_limiter import limiter, user_or_ip_key
from app.services.ws_manager import ws_manager

router = APIRouter()


async def _get_owned_appointment(
    db: AsyncSession,
    appointment_id: int,
    user_id: int,
) -> Appointment:
    result = await db.execute(
        select(Appointment)
        .join(Patient, Appointment.patient_id == Patient.id)
        .filter(Appointment.id == appointment_id, Patient.user_id == user_id)
    )
    appointment = result.scalars().first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    return appointment

class AppointmentCreate(BaseModel):
    doctor_id: int = Field(gt=0)
    department_id: int = Field(gt=0)
    scheduled_time: datetime
    symptoms: Optional[str] = None

class AppointmentResponse(BaseModel):
    id: int
    doctor_name: str
    department_name: str
    scheduled_time: datetime
    status: str
    queue_position: int
    estimated_wait_minutes: int

@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute", key_func=user_or_ip_key)
async def book_appointment(
    request: Request,
    response: Response,
    appointment: AppointmentCreate,
    current_user = Depends(deps.check_role(["patient"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Book a new appointment and return real-time queue position
    """
    user_id = current_user.id
    patient_res = await db.execute(select(Patient).filter(Patient.user_id == user_id))
    patient = patient_res.scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found.")

    scheduled_time = database_datetime(appointment.scheduled_time)
    if scheduled_time <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=422, detail="Appointment time must be in the future.")

    doc_res = await db.execute(select(Doctor).filter(Doctor.id == appointment.doctor_id))
    doctor = doc_res.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found.")
    if doctor.department_id != appointment.department_id:
        raise HTTPException(status_code=422, detail="Doctor does not belong to the selected department.")
    if not doctor.is_available:
        raise HTTPException(status_code=409, detail="Doctor is not currently accepting appointments.")

    dept_res = await db.execute(select(Department).filter(Department.id == appointment.department_id))
    department = dept_res.scalars().first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found.")

    # Keep the position scoped to the doctor's current operating day.
    day_start = datetime.combine(scheduled_time.date(), time.min)
    day_end = datetime.combine(scheduled_time.date(), time.max)
    active_res = await db.execute(
        select(Appointment.id).filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.status == "scheduled",
            Appointment.scheduled_time >= day_start,
            Appointment.scheduled_time <= day_end,
        )
    )
    active_count = len(active_res.all())
    available_slots = await get_available_slots(db, doctor, scheduled_time.date())
    if scheduled_time.isoformat() not in available_slots:
        raise HTTPException(status_code=409, detail="Selected appointment time is not available.")
    new_position = active_count + 1
    avg_consultation_time = max(doctor.avg_consultation_time, 1)
    wait_time_minutes = new_position * avg_consultation_time

    db_apt = Appointment(
        patient_id=patient.id,
        doctor_id=appointment.doctor_id,
        department_id=appointment.department_id,
        scheduled_time=scheduled_time,
        status="scheduled",
        queue_position=new_position,
        wait_time_minutes=wait_time_minutes,
        symptoms=appointment.symptoms
    )
    db.add(db_apt)
    await db.commit()
    await db.refresh(db_apt)

    event_data = {
        "appointment_id": db_apt.id,
        "doctor_id": db_apt.doctor_id,
        "patient_id": db_apt.patient_id,
        "scheduled_time": db_apt.scheduled_time.isoformat(),
        "status": db_apt.status,
        "queue_position": db_apt.queue_position,
    }
    await ws_manager.broadcast_event(f"doctor:{db_apt.doctor_id}", "queue_update", event_data)
    await ws_manager.broadcast_event(f"patient:{db_apt.patient_id}", "queue_update", event_data)

    return {
        "id": db_apt.id,
        "doctor_name": f"{doctor.first_name} {doctor.last_name}",
        "department_name": department.name,
        "scheduled_time": db_apt.scheduled_time,
        "status": db_apt.status,
        "queue_position": db_apt.queue_position,
        "estimated_wait_minutes": db_apt.wait_time_minutes
    }

@router.get("", response_model=List[AppointmentResponse])
@router.get("/", response_model=List[AppointmentResponse])
async def list_appointments(
    upcoming: Optional[bool] = None,
    current_user = Depends(deps.check_role(["patient"])),
    db: AsyncSession = Depends(get_db),
):
    """
    List user appointments
    """
    user_id = current_user.id
    patient_res = await db.execute(select(Patient).filter(Patient.user_id == user_id))
    patient = patient_res.scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found.")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    query = (
        select(Appointment, Doctor, Department)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(Department, Appointment.department_id == Department.id)
        .where(Appointment.patient_id == patient.id)
    )
    if upcoming is True:
        query = query.where(
            Appointment.scheduled_time >= now,
            Appointment.status.not_in(["cancelled", "completed"]),
        )
    elif upcoming is False:
        query = query.where(
            or_(
                Appointment.scheduled_time < now,
                Appointment.status.in_(["cancelled", "completed"]),
            )
        )
    result = await db.execute(query.order_by(Appointment.scheduled_time.asc()))
    return [
        {
            "id": apt.id,
            "doctor_name": f"{doctor.first_name} {doctor.last_name}",
            "department_name": department.name,
            "scheduled_time": apt.scheduled_time,
            "status": apt.status,
            "queue_position": apt.queue_position,
            "estimated_wait_minutes": apt.wait_time_minutes
        }
        for apt, doctor, department in result.all()
    ]

@router.get("/queue")
async def get_queue_status(
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current queue status across active clinics
    """
    result = await db.execute(
        select(Appointment)
        .where(
            Appointment.status.in_(["check_in", "treating"]),
            Appointment.queue_position > 0,
        )
        .order_by(Appointment.queue_position.asc(), Appointment.scheduled_time.asc())
    )
    active_apts = result.scalars().all()
    waiting = [appointment for appointment in active_apts if appointment.status == "check_in"]
    average_wait = (
        round(sum(appointment.wait_time_minutes for appointment in waiting) / len(waiting))
        if waiting
        else 0
    )
    return {
        "total_waiting": len(waiting),
        "average_wait_minutes": average_wait,
        "queue": [
            {
                "appointment_id": a.id,
                "doctor_id": a.doctor_id,
                "position": a.queue_position,
                "status": a.status
            }
            for a in active_apts[:10]
        ]
    }

@router.get("/doctor/{doctor_id}/availability")
async def get_doctor_availability(
    doctor_id: int,
    for_date: date = Query(default_factory=date.today, alias="date"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get real-time slots and availability for a doctor
    """
    doc_res = await db.execute(select(Doctor).filter(Doctor.id == doctor_id))
    doctor = doc_res.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found.")
    
    return {
        "doctor_id": doctor.id,
        "is_available": doctor.is_available,
        "max_patients_per_day": doctor.max_patients_per_day,
        "current_patients": doctor.current_patients,
        "available_slots": await get_available_slots(db, doctor, for_date),
    }

class AppointmentUpdate(BaseModel):
    scheduled_time: Optional[datetime] = None
    symptoms: Optional[str] = None

@router.get("/{id}", response_model=AppointmentResponse)
async def get_appointment(
    id: int,
    current_user = Depends(deps.check_role(["patient"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Get appointment details
    """
    result = await db.execute(
        select(Appointment, Doctor, Department)
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(Department, Appointment.department_id == Department.id)
        .where(Appointment.id == id, Patient.user_id == current_user.id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    apt, doctor, department = row
    return {
        "id": apt.id,
        "doctor_name": f"{doctor.first_name} {doctor.last_name}",
        "department_name": department.name,
        "scheduled_time": apt.scheduled_time,
        "status": apt.status,
        "queue_position": apt.queue_position,
        "estimated_wait_minutes": apt.wait_time_minutes
    }

@router.put("/{id}")
async def update_appointment(
    id: int,
    update_data: AppointmentUpdate,
    current_user = Depends(deps.check_role(["patient"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Update appointment details
    """
    apt = await _get_owned_appointment(db, id, current_user.id)
    if apt.status != "scheduled":
        raise HTTPException(status_code=409, detail="Only scheduled appointments can be changed.")

    changes = update_data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one appointment field is required.")
    if update_data.scheduled_time is not None:
        new_time = database_datetime(update_data.scheduled_time)
        if new_time <= datetime.now(timezone.utc).replace(tzinfo=None):
            raise HTTPException(status_code=422, detail="Appointment time must be in the future.")
        doctor_result = await db.execute(select(Doctor).where(Doctor.id == apt.doctor_id))
        doctor = doctor_result.scalar_one_or_none()
        if doctor is None:
            raise HTTPException(status_code=404, detail="Doctor not found.")
        slots = await get_available_slots(db, doctor, new_time.date())
        if new_time == database_datetime(apt.scheduled_time):
            slots.append(new_time.isoformat())
        if new_time.isoformat() not in slots:
            raise HTTPException(status_code=409, detail="Selected appointment time is not available.")
        apt.scheduled_time = new_time
    if update_data.symptoms is not None:
        apt.symptoms = update_data.symptoms

    await db.commit()
    return {"message": f"Appointment {id} updated successfully"}

@router.delete("/{id}")
async def cancel_appointment(
    id: int,
    current_user = Depends(deps.check_role(["patient"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel an appointment
    """
    target_id = id
    apt = await _get_owned_appointment(db, target_id, current_user.id)
    if apt.status != "scheduled":
        raise HTTPException(status_code=409, detail="Only scheduled appointments can be cancelled.")

    apt.status = "cancelled"
    await db.commit()
    event_data = {
        "appointment_id": apt.id,
        "doctor_id": apt.doctor_id,
        "patient_id": apt.patient_id,
        "status": apt.status,
    }
    await ws_manager.broadcast_event(f"doctor:{apt.doctor_id}", "queue_update", event_data)
    await ws_manager.broadcast_event(f"patient:{apt.patient_id}", "queue_update", event_data)
    return {"message": f"Appointment {target_id} canceled successfully"}
