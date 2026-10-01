import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models.user import User
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor, Department
from app.models.hospital import StaffSchedule
from app.models.patient import Patient
from app.schemas.doctor import Doctor as DoctorSchema

router = APIRouter()


class DoctorProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    specialization: Optional[str] = Field(None, min_length=1, max_length=100)
    years_of_experience: Optional[int] = Field(None, ge=0, le=80)
    is_available: Optional[bool] = None
    phone: Optional[str] = Field(None, min_length=1, max_length=20)


class ScheduleCreate(BaseModel):
    date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    shift_type: str = Field(default="regular", min_length=1, max_length=20)
    is_available: bool = True


class PatientNoteCreate(BaseModel):
    appointment_id: int = Field(gt=0)
    notes: str = Field(min_length=1)


@router.get("/profile")
async def get_current_doctor_profile(
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Doctor).where(Doctor.user_id == current_user.id))
    doctor = result.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    return {
        "id": doctor.id,
        "first_name": doctor.first_name,
        "last_name": doctor.last_name,
        "specialization": doctor.specialization,
        "years_of_experience": doctor.years_of_experience,
        "is_available": doctor.is_available,
        "email": current_user.email,
        "phone": current_user.phone,
    }


@router.put("/profile")
async def update_current_doctor_profile(
    profile_update: DoctorProfileUpdate,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Doctor).where(Doctor.user_id == current_user.id))
    doctor = result.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    changes = profile_update.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one profile field is required.")
    phone = changes.pop("phone", None)
    if phone is not None:
        phone = phone.strip()
        if not phone:
            raise HTTPException(status_code=422, detail="Phone number cannot be empty.")
        phone_result = await db.execute(
            select(User).where(User.phone == phone, User.id != current_user.id)
        )
        if phone_result.scalars().first():
            raise HTTPException(status_code=409, detail="This phone number is already in use.")
        current_user.phone = phone
    for field, value in changes.items():
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise HTTPException(status_code=422, detail=f"{field} cannot be empty.")
        setattr(doctor, field, value)
    await db.commit()
    await db.refresh(doctor)
    return {
        "id": doctor.id,
        "first_name": doctor.first_name,
        "last_name": doctor.last_name,
        "specialization": doctor.specialization,
        "years_of_experience": doctor.years_of_experience,
        "is_available": doctor.is_available,
        "email": current_user.email,
        "phone": current_user.phone,
    }


@router.get("/schedule")
async def get_doctor_schedule(
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    doctor_result = await db.execute(select(Doctor.id).where(Doctor.user_id == current_user.id))
    if doctor_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    result = await db.execute(
        select(StaffSchedule)
        .where(StaffSchedule.staff_id == current_user.id)
        .order_by(StaffSchedule.date.asc(), StaffSchedule.start_time.asc())
    )
    return {"items": result.scalars().all()}


@router.post("/schedule", status_code=status.HTTP_201_CREATED)
async def create_doctor_schedule(
    schedule: ScheduleCreate,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    doctor_result = await db.execute(select(Doctor.id).where(Doctor.user_id == current_user.id))
    if doctor_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    if schedule.start_time >= schedule.end_time:
        raise HTTPException(status_code=422, detail="Schedule start_time must precede end_time.")

    shift_date = datetime.datetime.combine(schedule.date, datetime.time.min)
    start_time = datetime.datetime.combine(schedule.date, schedule.start_time)
    end_time = datetime.datetime.combine(schedule.date, schedule.end_time)
    overlap_result = await db.execute(
        select(StaffSchedule.id)
        .where(
            StaffSchedule.staff_id == current_user.id,
            StaffSchedule.date == shift_date,
            StaffSchedule.start_time < end_time,
            StaffSchedule.end_time > start_time,
        )
        .limit(1)
    )
    if overlap_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Schedule overlaps an existing shift.")

    record = StaffSchedule(
        staff_id=current_user.id,
        date=shift_date,
        start_time=start_time,
        end_time=end_time,
        shift_type=schedule.shift_type,
        is_available=schedule.is_available,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/patients/{patient_id}/notes")
async def get_patient_notes(
    patient_id: int,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    doctor_result = await db.execute(select(Doctor.id).where(Doctor.user_id == current_user.id))
    doctor_id = doctor_result.scalar_one_or_none()
    if doctor_id is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    patient_result = await db.execute(select(Patient.id).where(Patient.id == patient_id))
    if patient_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    result = await db.execute(
        select(Appointment)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.doctor_id == doctor_id,
            Appointment.notes.is_not(None),
        )
        .order_by(Appointment.scheduled_time.desc())
    )
    return {
        "items": [
            {
                "appointment_id": appointment.id,
                "date": appointment.actual_time or appointment.scheduled_time,
                "status": appointment.status,
                "notes": appointment.notes,
            }
            for appointment in result.scalars().all()
        ]
    }


@router.post("/patients/{patient_id}/notes")
async def save_patient_note(
    patient_id: int,
    note: PatientNoteCreate,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    doctor_result = await db.execute(select(Doctor.id).where(Doctor.user_id == current_user.id))
    doctor_id = doctor_result.scalar_one_or_none()
    if doctor_id is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == note.appointment_id,
            Appointment.patient_id == patient_id,
            Appointment.doctor_id == doctor_id,
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Doctor appointment for patient not found.")
    appointment.notes = note.notes
    await db.commit()
    await db.refresh(appointment)
    return {
        "appointment_id": appointment.id,
        "patient_id": appointment.patient_id,
        "notes": appointment.notes,
        "updated_at": appointment.updated_at,
    }


# =========================================================
# PUBLIC DOCTOR ENDPOINTS
# These are the ones causing the MissingGreenlet error
# =========================================================

@router.get("", response_model=List[DoctorSchema])
@router.get("/", response_model=List[DoctorSchema])
async def list_doctors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Doctor).options(selectinload(Doctor.department))
    )
    return result.scalars().all()


@router.get("/available", response_model=List[DoctorSchema])
async def get_available_doctors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Doctor)
        .options(selectinload(Doctor.department))
        .filter(Doctor.is_available == True)
    )
    return result.scalars().all()


@router.get("/department/{department_id}", response_model=List[DoctorSchema])
async def get_doctors_by_dept(department_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Doctor)
        .options(selectinload(Doctor.department))
        .filter(Doctor.department_id == department_id)
    )
    return result.scalars().all()


@router.put("/availability")
async def update_availability(
    id: int,
    available: bool,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Doctor).filter(Doctor.id == id))
    doctor = result.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if doctor.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update your own availability.")
    doctor.is_available = available
    await db.commit()
    return {"message": "Availability updated"}


@router.get("/{id}", response_model=DoctorSchema)
async def get_doctor(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Doctor)
        .options(selectinload(Doctor.department))
        .filter(Doctor.id == id)
    )
    doctor = result.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor