from fastapi import APIRouter, Depends, HTTPException, status
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.db.session import get_db
from app.models.patient import Patient
from app.models.user import User
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.vitals import PatientVitals
from app.schemas.vitals import PatientVitals as PatientVitalsSchema
from app.schemas.vitals import PatientVitalsCreate
from app.core.rbac import require_permission

router = APIRouter()
VITALS_WRITE_ROLES = {"doctor", "staff", "nurse", "admin"}


async def _verify_doctor_patient_access(
    db: AsyncSession,
    user_id: int,
    patient_id: int,
) -> None:
    doctor_result = await db.execute(select(Doctor.id).where(Doctor.user_id == user_id))
    doctor_id = doctor_result.scalar_one_or_none()
    if doctor_id is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    appointment_result = await db.execute(
        select(Appointment.id)
        .where(
            Appointment.doctor_id == doctor_id,
            Appointment.patient_id == patient_id,
        )
        .limit(1)
    )
    if appointment_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="You are not assigned to this patient.")


class PatientProfile(BaseModel):
    id: Optional[int] = None
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[List[str]] = None
    emergency_contact: str
    emergency_contact_name: str
    medical_history: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    total_visits: int = 0
    last_visit_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class PatientProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, pattern="^(male|female|other|unknown)$")
    blood_group: Optional[str] = Field(None, pattern="^(A|B|AB|O)[+-]$")
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    allergies: Optional[List[str]] = None
    emergency_contact: Optional[str] = Field(None, min_length=7, max_length=20)
    emergency_contact_name: Optional[str] = Field(None, min_length=2, max_length=100)
    medical_history: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_number: Optional[str] = None

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: Optional[date]) -> Optional[date]:
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value

    @field_validator("phone")
    @classmethod
    def validate_indian_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            digits = "".join(character for character in value if character.isdigit())
            if len(digits) == 12 and digits.startswith("91"):
                digits = digits[2:]
            if len(digits) != 10 or digits[0] not in "6789":
                raise ValueError("Enter a valid Indian phone number.")
            return digits
        return value

    @field_validator("emergency_contact", "emergency_contact_name", mode="before")
    @classmethod
    def normalize_optional_emergency_contact(cls, value: Optional[str]) -> Optional[str]:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


@router.get("/vitals")
async def get_patient_vitals(
    patient_id: Optional[int] = None,
    current_user=Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "patient":
        result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = result.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found.")
        if patient_id is not None and patient_id != patient.id:
            raise HTTPException(status_code=403, detail="You may only access your own vitals.")
        target_patient_id = patient.id
    elif current_user.role in VITALS_WRITE_ROLES:
        if patient_id is None:
            raise HTTPException(status_code=422, detail="patient_id is required for staff access.")
        target_patient_id = patient_id
    else:
        raise HTTPException(status_code=403, detail="Vitals access is not authorized.")

    patient_result = await db.execute(select(Patient.id).where(Patient.id == target_patient_id))
    if patient_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    if current_user.role == "doctor":
        await _verify_doctor_patient_access(db, current_user.id, target_patient_id)

    result = await db.execute(
        select(PatientVitals)
        .where(PatientVitals.patient_id == target_patient_id)
        .order_by(PatientVitals.recorded_at.desc(), PatientVitals.id.desc())
    )
    return {"items": [PatientVitalsSchema.model_validate(item) for item in result.scalars().all()]}


@router.post("/vitals", response_model=PatientVitalsSchema, status_code=status.HTTP_201_CREATED)
async def record_patient_vitals(
    vitals: PatientVitalsCreate,
    current_user=Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in VITALS_WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Vitals entry is not authorized.")

    patient_result = await db.execute(select(Patient.id).where(Patient.id == vitals.patient_id))
    if patient_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    if current_user.role == "doctor":
        await _verify_doctor_patient_access(db, current_user.id, vitals.patient_id)

    record = PatientVitals(**vitals.model_dump(), recorded_by_id=current_user.id)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record

@router.get("/profile", response_model=PatientProfile)
async def get_profile(
    current_user = Depends(require_permission("view_own_profile")),
    db: AsyncSession = Depends(get_db)
):
    """
    Get patient medical and personal details
    """
    user_id = current_user.id
    result = await db.execute(select(Patient).filter(Patient.user_id == user_id))
    patient = result.scalars().first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found."
        )
    visits_result = await db.execute(
        select(Appointment)
        .where(Appointment.patient_id == patient.id, Appointment.status == "completed")
        .order_by(Appointment.actual_time.desc(), Appointment.scheduled_time.desc())
    )
    visits = visits_result.scalars().all()
    last_visit = (visits[0].actual_time or visits[0].scheduled_time) if visits else None
    date_of_birth = patient.date_of_birth
    if isinstance(date_of_birth, datetime):
        date_of_birth = date_of_birth.date()
    return {
        "id": patient.id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "blood_group": patient.blood_group,
        "allergies": patient.allergies,
        "emergency_contact": patient.emergency_contact,
        "emergency_contact_name": patient.emergency_contact_name,
        "medical_history": patient.medical_history,
        "insurance_provider": patient.insurance_provider,
        "insurance_number": patient.insurance_number,
        "date_of_birth": date_of_birth.isoformat() if date_of_birth else None,
        "gender": patient.gender,
        "total_visits": len(visits),
        "last_visit_date": last_visit.date() if last_visit else None,
    }

@router.put("/profile")
async def update_profile(
    profile_update: PatientProfileUpdate,
    current_user = Depends(require_permission("manage_own_profile")),
    db: AsyncSession = Depends(get_db)
):
    """
    Update patient profile details
    """
    user_id = current_user.id
    result = await db.execute(select(Patient).filter(Patient.user_id == user_id))
    patient = result.scalars().first()
    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found."
        )

    changes = profile_update.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one profile field is required.")

    for field in ("phone", "email"):
        if field in changes:
            value = changes.pop(field)
            value = str(value).strip().lower() if field == "email" else value
            duplicate = await db.execute(
                select(User.id).where(
                    getattr(User, field) == value,
                    User.id != current_user.id,
                )
            )
            if duplicate.scalar_one_or_none() is not None:
                raise HTTPException(status_code=409, detail=f"{field.capitalize()} is already in use.")
            setattr(current_user, field, value)

    for field, value in changes.items():
        setattr(patient, field, value)

    await db.commit()
    return {"message": "Profile updated successfully", "data": profile_update}

@router.get("/history")
async def get_history(
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get patient medical records, visit history, and prescription history
    """
    from app.models.pharmacy import Prescription

    user_id = current_user.id
    result = await db.execute(select(Patient).filter(Patient.user_id == user_id))
    patient = result.scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found.")

    # 1. Query appointments
    apt_res = await db.execute(
        select(Appointment, Doctor)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .filter(Appointment.patient_id == patient.id)
        .order_by(Appointment.scheduled_time.desc())
    )

    history = []
    for appointment, doctor in apt_res.all():
        history.append({
            "type": "visit",
            "date": (appointment.actual_time or appointment.scheduled_time).date().isoformat(),
            "diagnosis": appointment.symptoms or "General Consultation",
            "treatment": appointment.notes or f"Consultation with Dr. {doctor.first_name} {doctor.last_name}",
            "doctor": f"Dr. {doctor.first_name} {doctor.last_name}",
            "notes": appointment.notes,
        })

    # 2. Query prescriptions
    rx_res = await db.execute(
        select(Prescription, Doctor)
        .join(Doctor, Prescription.doctor_id == Doctor.id)
        .filter(Prescription.patient_id == patient.id)
        .order_by(Prescription.created_at.desc())
    )

    for prescription, doctor in rx_res.all():
        history.append({
            "type": "prescription",
            "date": prescription.created_at.date().isoformat() if prescription.created_at else None,
            "diagnosis": f"Prescription: {prescription.medication}",
            "treatment": f"{prescription.dosage} - {prescription.frequency} ({prescription.duration})",
            "doctor": f"Dr. {doctor.first_name} {doctor.last_name}",
            "notes": prescription.instructions or f"Status: {prescription.status}",
        })

    if patient.medical_history:
        history.append({
            "type": "notes",
            "date": patient.updated_at.date().isoformat() if patient.updated_at else None,
            "diagnosis": "Medical History Record",
            "treatment": "Patient Self-Reported History",
            "doctor": None,
            "notes": patient.medical_history,
        })

    # Sort history by date descending
    history.sort(key=lambda x: x["date"] or "", reverse=True)
    return {"history": history}

@router.post("/medical-history")
async def add_medical_history(
    notes: str,
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a manual entry to medical history
    """
    user_id = current_user.id
    result = await db.execute(select(Patient).filter(Patient.user_id == user_id))
    patient = result.scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    patient.medical_history = "\n".join(filter(None, [patient.medical_history, notes]))
    await db.commit()
    return {"message": "Medical history added", "notes": notes}

@router.get("/emergency-contact")
async def get_emergency_contact(
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get emergency contact details
    """
    user_id = current_user.id
    result = await db.execute(select(Patient).filter(Patient.user_id == user_id))
    patient = result.scalars().first()
    if not patient:
        return {"name": "Not set", "phone": ""}
    return {"name": patient.emergency_contact_name, "phone": patient.emergency_contact}

@router.put("/emergency-contact")
async def update_emergency_contact(
    name: str,
    phone: str,
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update patient emergency contacts
    """
    user_id = current_user.id
    result = await db.execute(select(Patient).filter(Patient.user_id == user_id))
    patient = result.scalars().first()
    if patient:
        patient.emergency_contact_name = name
        patient.emergency_contact = phone
        await db.commit()
    return {"message": "Emergency contact updated successfully"}

@router.get("/qr-code")
async def get_patient_qr_code(
    current_user = Depends(deps.get_current_active_user)
):
    """
    Generate and return the patient's unique QR ID
    """
    return {
        "qr_data": f"NAVIORA-{current_user.id}",
        "label": "Show this at reception"
    }
