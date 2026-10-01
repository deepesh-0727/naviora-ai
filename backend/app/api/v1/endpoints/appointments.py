from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime, time
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.doctor import Doctor, Department

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
    doctor_id: int
    department_id: int
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
async def book_appointment(
    appointment: AppointmentCreate,
    current_user = Depends(deps.get_current_active_user),
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

    doc_res = await db.execute(select(Doctor).filter(Doctor.id == appointment.doctor_id))
    doctor = doc_res.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found.")

    dept_res = await db.execute(select(Department).filter(Department.id == appointment.department_id))
    department = dept_res.scalars().first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found.")

    # Keep the position scoped to the doctor's current operating day.
    day_start = datetime.combine(appointment.scheduled_time.date(), time.min)
    day_end = datetime.combine(appointment.scheduled_time.date(), time.max)
    active_res = await db.execute(
        select(Appointment.id).filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.status == "scheduled",
            Appointment.scheduled_time >= day_start,
            Appointment.scheduled_time <= day_end,
        )
    )
    active_count = len(active_res.all())
    new_position = active_count + 1
    avg_consultation_time = doctor.avg_consultation_time if doctor.avg_consultation_time else 15
    wait_time_minutes = new_position * avg_consultation_time

    db_apt = Appointment(
        patient_id=patient.id,
        doctor_id=appointment.doctor_id,
        department_id=appointment.department_id,
        scheduled_time=appointment.scheduled_time,
        status="scheduled",
        queue_position=new_position,
        wait_time_minutes=wait_time_minutes,
        symptoms=appointment.symptoms
    )
    db.add(db_apt)
    await db.commit()
    await db.refresh(db_apt)

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
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user appointments
    """
    user_id = current_user.id
    patient_res = await db.execute(select(Patient).filter(Patient.user_id == user_id))
    patient = patient_res.scalars().first()
    if not patient:
        return []

    result = await db.execute(
        select(Appointment).filter(Appointment.patient_id == patient.id)
    )
    appointments = result.scalars().all()

    response = []
    for apt in appointments:
        doc_res = await db.execute(select(Doctor).filter(Doctor.id == apt.doctor_id))
        doc = doc_res.scalars().first()
        dept_res = await db.execute(select(Department).filter(Department.id == apt.department_id))
        dept = dept_res.scalars().first()
        
        response.append({
            "id": apt.id,
            "doctor_name": f"{doc.first_name} {doc.last_name}" if doc else "Unknown Doctor",
            "department_name": dept.name if dept else "Unknown Dept",
            "scheduled_time": apt.scheduled_time,
            "status": apt.status,
            "queue_position": apt.queue_position,
            "estimated_wait_minutes": apt.wait_time_minutes
        })
    return response

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
        "available_slots": [
            "09:00 AM", "10:00 AM", "11:30 AM", "02:00 PM", "03:30 PM", "04:30 PM"
        ]
    }

class AppointmentUpdate(BaseModel):
    scheduled_time: Optional[datetime] = None
    status: Optional[str] = None
    symptoms: Optional[str] = None
    notes: Optional[str] = None

@router.get("/{id}", response_model=AppointmentResponse)
async def get_appointment(
    id: int,
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get appointment details
    """
    apt = await _get_owned_appointment(db, id, current_user.id)

    doc_res = await db.execute(select(Doctor).filter(Doctor.id == apt.doctor_id))
    doc = doc_res.scalars().first()
    dept_res = await db.execute(select(Department).filter(Department.id == apt.department_id))
    dept = dept_res.scalars().first()

    return {
        "id": apt.id,
        "doctor_name": f"{doc.first_name} {doc.last_name}" if doc else "Unknown Doctor",
        "department_name": dept.name if dept else "Unknown Dept",
        "scheduled_time": apt.scheduled_time,
        "status": apt.status,
        "queue_position": apt.queue_position,
        "estimated_wait_minutes": apt.wait_time_minutes
    }

@router.put("/{id}")
async def update_appointment(
    id: int,
    update_data: AppointmentUpdate,
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update appointment details
    """
    apt = await _get_owned_appointment(db, id, current_user.id)
    
    if update_data.scheduled_time:
        apt.scheduled_time = update_data.scheduled_time
    if update_data.status:
        apt.status = update_data.status
    if update_data.symptoms:
        apt.symptoms = update_data.symptoms
    if update_data.notes:
        apt.notes = update_data.notes

    await db.commit()
    return {"message": f"Appointment {id} updated successfully"}

@router.delete("/{id}")
async def cancel_appointment(
    id: Optional[int] = None,
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel an appointment
    """
    target_id = id
    apt = await _get_owned_appointment(db, target_id, current_user.id)
    
    apt.status = "cancelled"
    await db.commit()
    return {"message": f"Appointment {target_id} canceled successfully"}
