from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.bed import Bed
from app.models.doctor import Doctor
from app.models.operations import Admission, LabOrder, Referral
from app.models.patient import Patient
from app.models.pharmacy import Prescription
from app.models.user import User
from app.services.ws_manager import ws_manager

router = APIRouter()


class PrescriptionCreate(BaseModel):
    patient_id: int = Field(gt=0)
    appointment_id: int = Field(gt=0)
    medication: str = Field(min_length=1, max_length=100)
    dosage: str = Field(min_length=1, max_length=50)
    frequency: str = Field(min_length=1, max_length=50)
    duration: str = Field(min_length=1, max_length=50)
    instructions: str | None = None


class LabOrderCreate(BaseModel):
    patient_id: int = Field(gt=0)
    test_name: str = Field(min_length=1, max_length=160)
    category: str | None = None
    appointment_id: int | None = None
    notes: str | None = None


class ReferralCreate(BaseModel):
    patient_id: int = Field(gt=0)
    specialty: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=4000)
    department_id: int | None = None


class AdmissionCreate(BaseModel):
    patient_id: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=4000)
    bed_id: int | None = None


async def _doctor(db: AsyncSession, user: User) -> Doctor:
    result = await db.execute(select(Doctor).where(Doctor.user_id == user.id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    return doctor


async def _patient_and_appointment(db: AsyncSession, user: User, patient_id: int, appointment_id: int) -> tuple[Patient, Appointment, Doctor]:
    patient = await db.get(Patient, patient_id)
    appointment = await db.get(Appointment, appointment_id)
    doctor = await _doctor(db, user)
    if patient is None or appointment is None or appointment.patient_id != patient_id or appointment.doctor_id != doctor.id:
        raise HTTPException(status_code=404, detail="Patient appointment not found for this doctor.")
    return patient, appointment, doctor


async def _patient(db: AsyncSession, patient_id: int) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return patient


@router.post("/prescriptions", status_code=status.HTTP_201_CREATED)
async def create_prescription(
    payload: PrescriptionCreate,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    _, appointment, doctor = await _patient_and_appointment(db, current_user, payload.patient_id, payload.appointment_id)
    prescription = Prescription(
        appointment_id=appointment.id,
        patient_id=payload.patient_id,
        doctor_id=doctor.id,
        medication=payload.medication.strip(),
        dosage=payload.dosage.strip(),
        frequency=payload.frequency.strip(),
        duration=payload.duration.strip(),
        instructions=payload.instructions,
        status="pending",
    )
    db.add(prescription)
    await db.commit()
    await db.refresh(prescription)
    await ws_manager.broadcast_event("pharmacy", "prescription_new", {
        "prescription_id": prescription.id,
        "patient_id": prescription.patient_id,
        "medication": prescription.medication,
        "status": prescription.status,
    })
    return prescription


@router.post("/lab-orders", status_code=status.HTTP_201_CREATED)
async def create_lab_order(
    payload: LabOrderCreate,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    await _patient(db, payload.patient_id)
    doctor = await _doctor(db, current_user)
    if payload.appointment_id is not None:
        _, appointment, _ = await _patient_and_appointment(db, current_user, payload.patient_id, payload.appointment_id)
    else:
        appointment = None
        assigned = await db.scalar(select(Appointment.id).where(Appointment.patient_id == payload.patient_id, Appointment.doctor_id == doctor.id).limit(1))
        if assigned is None:
            raise HTTPException(status_code=403, detail="You are not assigned to this patient.")
    order = LabOrder(
        patient_id=payload.patient_id,
        ordered_by_id=current_user.id,
        appointment_id=appointment.id if appointment else None,
        test_name=payload.test_name.strip(),
        category=payload.category,
        notes=payload.notes,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    await ws_manager.broadcast_event("pharmacy", "lab_order_new", {
        "lab_order_id": order.id,
        "patient_id": order.patient_id,
        "test_name": order.test_name,
    })
    return order


@router.post("/referrals", status_code=status.HTTP_201_CREATED)
async def create_referral(
    payload: ReferralCreate,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    await _patient(db, payload.patient_id)
    doctor = await _doctor(db, current_user)
    assigned = await db.scalar(select(Appointment.id).where(Appointment.patient_id == payload.patient_id, Appointment.doctor_id == doctor.id).limit(1))
    if assigned is None:
        raise HTTPException(status_code=403, detail="You are not assigned to this patient.")
    referral = Referral(patient_id=payload.patient_id, referring_doctor_id=doctor.id, department_id=payload.department_id, specialty=payload.specialty.strip(), reason=payload.reason.strip())
    db.add(referral)
    await db.commit()
    await db.refresh(referral)
    return referral


@router.post("/admissions", status_code=status.HTTP_201_CREATED)
async def admit_patient(
    payload: AdmissionCreate,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    await _patient(db, payload.patient_id)
    doctor = await _doctor(db, current_user)
    assigned = await db.scalar(select(Appointment.id).where(Appointment.patient_id == payload.patient_id, Appointment.doctor_id == doctor.id).limit(1))
    if assigned is None:
        raise HTTPException(status_code=403, detail="You are not assigned to this patient.")
    bed = None
    if payload.bed_id is not None:
        bed = await db.get(Bed, payload.bed_id, with_for_update=True)
        if bed is None or bed.status != "available" or bed.patient_id is not None:
            raise HTTPException(status_code=409, detail="The selected bed is not available.")
        bed.status = "occupied"
        bed.patient_id = payload.patient_id
    admission = Admission(patient_id=payload.patient_id, doctor_id=doctor.id, bed_id=bed.id if bed else None, admitted_by_id=current_user.id, reason=payload.reason.strip(), admitted_at=datetime.utcnow())
    db.add(admission)
    await db.commit()
    await db.refresh(admission)
    return admission
