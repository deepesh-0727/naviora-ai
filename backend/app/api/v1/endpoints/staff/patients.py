from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.operations import LabOrder
from app.models.patient import Patient
from app.models.pharmacy import Prescription
from app.models.user import User
from app.models.vitals import PatientVitals

router = APIRouter()


async def _authorized_patient(db: AsyncSession, user: User, patient_id: int) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found.")
    doctor_id = await db.scalar(select(Doctor.id).where(Doctor.user_id == user.id))
    if doctor_id is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    appointment_id = await db.scalar(
        select(Appointment.id).where(Appointment.doctor_id == doctor_id, Appointment.patient_id == patient_id).limit(1)
    )
    if appointment_id is None:
        raise HTTPException(status_code=403, detail="You are not assigned to this patient.")
    return patient


@router.get("/{patient_id}")
async def patient_detail(
    patient_id: int,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    patient = await _authorized_patient(db, current_user, patient_id)
    return {
        "id": patient.id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "date_of_birth": patient.date_of_birth,
        "gender": patient.gender,
        "blood_group": patient.blood_group,
        "allergies": patient.allergies,
        "emergency_contact": patient.emergency_contact,
        "emergency_contact_name": patient.emergency_contact_name,
        "medical_history": patient.medical_history,
    }


@router.get("/{patient_id}/history")
async def patient_history(
    patient_id: int,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    await _authorized_patient(db, current_user, patient_id)
    result = await db.execute(select(Appointment).where(Appointment.patient_id == patient_id).order_by(Appointment.scheduled_time.desc()))
    return {"items": [{
        "id": appointment.id,
        "department_id": appointment.department_id,
        "scheduled_time": appointment.scheduled_time,
        "actual_time": appointment.actual_time,
        "status": appointment.status,
        "symptoms": appointment.symptoms,
        "notes": appointment.notes,
    } for appointment in result.scalars().all()]}


@router.get("/{patient_id}/vitals")
async def patient_vitals(
    patient_id: int,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    await _authorized_patient(db, current_user, patient_id)
    result = await db.execute(select(PatientVitals).where(PatientVitals.patient_id == patient_id).order_by(PatientVitals.recorded_at.desc()))
    return {"items": result.scalars().all()}


@router.get("/{patient_id}/labs")
async def patient_labs(
    patient_id: int,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    await _authorized_patient(db, current_user, patient_id)
    result = await db.execute(select(LabOrder).where(LabOrder.patient_id == patient_id).order_by(LabOrder.created_at.desc()))
    return {"items": result.scalars().all()}


@router.get("/{patient_id}/prescriptions")
async def patient_prescriptions(
    patient_id: int,
    current_user: User = Depends(deps.check_role(["doctor"])),
    db: AsyncSession = Depends(get_db),
):
    await _authorized_patient(db, current_user, patient_id)
    result = await db.execute(select(Prescription).where(Prescription.patient_id == patient_id).order_by(Prescription.created_at.desc()))
    return {"items": result.scalars().all()}
