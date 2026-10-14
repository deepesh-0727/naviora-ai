from datetime import date, datetime, time, timedelta
from decimal import Decimal
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.billing import Billing
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User

router = APIRouter()


class WalkInCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=20)
    date_of_birth: date
    gender: str = Field(pattern="^(male|female|other|unknown)$")
    emergency_contact: str = Field(min_length=7, max_length=20)
    emergency_contact_name: str = Field(min_length=2, max_length=100)


class AppointmentCreate(BaseModel):
    patient_id: int = Field(gt=0)
    doctor_id: int = Field(gt=0)
    scheduled_time: datetime
    symptoms: str | None = None


class BillingCreate(BaseModel):
    patient_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    appointment_id: int | None = None
    description: str = Field(min_length=2, max_length=300)


@router.get("/patients/search")
async def search_patients(
    q: str = Query(min_length=1, max_length=100),
    current_user: User = Depends(deps.check_role(["front_desk", "doctor", "nurse", "staff"])),
    db: AsyncSession = Depends(get_db),
):
    search = f"%{q.strip()}%"
    match = or_(User.phone.ilike(search), User.email.ilike(search))
    if q.strip().isdigit():
        match = or_(match, Patient.id == int(q.strip()))
    query = select(Patient, User).join(User, User.id == Patient.user_id).where(match).order_by(Patient.id.desc()).limit(50)
    result = await db.execute(query)
    return {"items": [{
        "id": patient.id,
        "full_name": f"{patient.first_name} {patient.last_name}",
        "phone": user.phone,
        "email": user.email,
    } for patient, user in result.all()]}


@router.post("/patients/walk-in", status_code=status.HTTP_201_CREATED)
async def register_walk_in(
    payload: WalkInCreate,
    current_user: User = Depends(deps.check_role(["front_desk", "staff"])),
    db: AsyncSession = Depends(get_db),
):
    if payload.date_of_birth > date.today():
        raise HTTPException(status_code=422, detail="Date of birth cannot be in the future.")
    duplicate = await db.scalar(select(User.id).where(or_(User.phone == payload.phone, User.email == str(payload.email))))
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="A patient already uses this phone number or email.")
    split_name = payload.full_name.strip().split(maxsplit=1)
    user = User(
        phone=payload.phone,
        email=str(payload.email),
        password_hash=get_password_hash(token_urlsafe(32)),
        role="patient",
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()
    patient = Patient(
        user_id=user.id,
        first_name=split_name[0],
        last_name=split_name[1] if len(split_name) > 1 else "",
        date_of_birth=datetime.combine(payload.date_of_birth, time.min),
        gender=payload.gender,
        emergency_contact=payload.emergency_contact,
        emergency_contact_name=payload.emergency_contact_name,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return {"patient_id": patient.id, "user_id": user.id, "verification_required": True}


@router.post("/appointments", status_code=status.HTTP_201_CREATED)
async def create_staff_appointment(
    payload: AppointmentCreate,
    current_user: User = Depends(deps.check_role(["front_desk", "staff"])),
    db: AsyncSession = Depends(get_db),
):
    if payload.scheduled_time <= datetime.utcnow():
        raise HTTPException(status_code=422, detail="Appointment time must be in the future.")
    patient_exists = await db.scalar(select(Patient.id).where(Patient.id == payload.patient_id))
    doctor = await db.get(Doctor, payload.doctor_id)
    if patient_exists is None:
        raise HTTPException(status_code=404, detail="Patient not found.")
    if doctor is None or not doctor.is_available:
        raise HTTPException(status_code=404, detail="Available doctor not found.")
    appointment = Appointment(
        patient_id=payload.patient_id,
        doctor_id=doctor.id,
        department_id=doctor.department_id,
        scheduled_time=payload.scheduled_time,
        symptoms=payload.symptoms,
        status="scheduled",
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.get("/doctors/load")
async def doctor_load(
    for_date: date | None = Query(default=None, alias="date"),
    current_user: User = Depends(deps.check_role(["front_desk", "staff", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    day = for_date or date.today()
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    result = await db.execute(
        select(Doctor, User.email, func.count(Appointment.id))
        .join(User, User.id == Doctor.user_id)
        .outerjoin(Appointment, (Appointment.doctor_id == Doctor.id) & (Appointment.scheduled_time >= start) & (Appointment.scheduled_time < end) & Appointment.status.notin_(["cancelled", "no_show"]))
        .where(Doctor.is_available.is_(True))
        .group_by(Doctor.id, User.email)
        .order_by(Doctor.last_name, Doctor.first_name)
    )
    return {"items": [{
        "doctor_id": doctor.id,
        "doctor_name": f"{doctor.first_name} {doctor.last_name}",
        "department_id": doctor.department_id,
        "specialization": doctor.specialization,
        "load": booked,
        "capacity": doctor.max_patients_per_day,
        "remaining_capacity": max(doctor.max_patients_per_day - booked, 0),
    } for doctor, _email, booked in result.all()]}


@router.get("/doctors/availability")
async def doctor_availability(
    doctor_id: int = Query(gt=0),
    for_date: date | None = Query(default=None, alias="date"),
    current_user: User = Depends(deps.check_role(["front_desk", "staff"])),
    db: AsyncSession = Depends(get_db),
):
    doctor = await db.get(Doctor, doctor_id)
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found.")
    day = for_date or date.today()
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    booked = await db.scalar(select(func.count(Appointment.id)).where(Appointment.doctor_id == doctor_id, Appointment.scheduled_time >= start, Appointment.scheduled_time < end, Appointment.status.notin_(["cancelled", "no_show"])))
    remaining = max(doctor.max_patients_per_day - (booked or 0), 0)
    return {"doctor_id": doctor_id, "date": day, "is_available": doctor.is_available and remaining > 0, "booked": booked or 0, "capacity": doctor.max_patients_per_day, "remaining_capacity": remaining}


@router.post("/payments", status_code=status.HTTP_201_CREATED)
async def create_billing_record(
    payload: BillingCreate,
    current_user: User = Depends(deps.check_role(["front_desk", "staff", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    patient_exists = await db.scalar(select(Patient.id).where(Patient.id == payload.patient_id))
    if patient_exists is None:
        raise HTTPException(status_code=404, detail="Patient not found.")
    if payload.appointment_id is not None:
        appointment_exists = await db.scalar(select(Appointment.id).where(Appointment.id == payload.appointment_id, Appointment.patient_id == payload.patient_id))
        if appointment_exists is None:
            raise HTTPException(status_code=404, detail="Patient appointment not found.")
    bill = Billing(
        patient_id=payload.patient_id,
        appointment_id=payload.appointment_id,
        amount=payload.amount,
        status="pending",
        invoice_number=f"INV-{uuid4().hex.upper()}",
        items={"description": payload.description},
    )
    db.add(bill)
    await db.commit()
    await db.refresh(bill)
    return {"id": bill.id, "invoice_number": bill.invoice_number, "status": bill.status, "amount": bill.amount}
