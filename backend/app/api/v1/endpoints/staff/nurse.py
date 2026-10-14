from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.bed import Bed
from app.models.operations import MedicationAdministration, NurseHandover
from app.models.patient import Patient
from app.models.user import User
from app.models.vitals import PatientVitals
from app.schemas.vitals import PatientVitalsCreate

router = APIRouter()


@router.get("/ward/{ward_id}/beds")
async def ward_beds(
    ward_id: str,
    current_user: User = Depends(deps.check_role(["nurse", "facilities", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Bed).where(Bed.ward == ward_id).order_by(Bed.bed_number))
    return {"items": result.scalars().all()}


@router.get("/ward/{ward_id}/medications/due")
async def medications_due(
    ward_id: str,
    current_user: User = Depends(deps.check_role(["nurse"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MedicationAdministration)
        .join(Bed, Bed.patient_id == MedicationAdministration.patient_id)
        .where(Bed.ward == ward_id, MedicationAdministration.status == "due", MedicationAdministration.due_at <= datetime.utcnow())
        .order_by(MedicationAdministration.due_at)
    )
    return {"items": result.scalars().all()}


@router.get("/ward/{ward_id}/vitals/due")
async def vitals_due(
    ward_id: str,
    current_user: User = Depends(deps.check_role(["nurse"])),
    db: AsyncSession = Depends(get_db),
):
    start_of_day = datetime.combine(datetime.utcnow().date(), time.min)
    last_vital = select(func.max(PatientVitals.recorded_at)).where(PatientVitals.patient_id == Bed.patient_id).correlate(Bed).scalar_subquery()
    result = await db.execute(
        select(Bed.patient_id, last_vital.label("last_recorded_at"))
        .where(Bed.ward == ward_id, Bed.status == "occupied", Bed.patient_id.is_not(None), (last_vital.is_(None) | (last_vital < start_of_day)))
        .order_by(Bed.bed_number)
    )
    return {"items": [{"patient_id": patient_id, "due_at": last_recorded_at, "reason": "No vitals recorded during the current day"} for patient_id, last_recorded_at in result.all()]}


@router.post("/vitals", status_code=201)
async def record_vitals(
    vitals: PatientVitalsCreate,
    current_user: User = Depends(deps.check_role(["nurse"])),
    db: AsyncSession = Depends(get_db),
):
    patient_exists = await db.scalar(select(Patient.id).where(Patient.id == vitals.patient_id))
    if patient_exists is None:
        raise HTTPException(status_code=404, detail="Patient not found.")
    record = PatientVitals(**vitals.model_dump(), recorded_by_id=current_user.id)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.post("/medications/record", status_code=201)
async def record_medication(
    payload: dict,
    current_user: User = Depends(deps.check_role(["nurse"])),
    db: AsyncSession = Depends(get_db),
):
    patient_id = payload.get("patient_id")
    medication = payload.get("details")
    if not isinstance(patient_id, int) or not isinstance(medication, str) or not medication.strip():
        raise HTTPException(status_code=422, detail="patient_id and medication details are required.")
    patient_exists = await db.scalar(select(Patient.id).where(Patient.id == patient_id))
    if patient_exists is None:
        raise HTTPException(status_code=404, detail="Patient not found.")
    record = MedicationAdministration(
        patient_id=patient_id,
        recorded_by_id=current_user.id,
        medication=medication.strip(),
        due_at=datetime.utcnow(),
        administered_at=datetime.utcnow(),
        status="administered",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.post("/handover", status_code=201)
async def submit_handover(
    payload: dict,
    current_user: User = Depends(deps.check_role(["nurse"])),
    db: AsyncSession = Depends(get_db),
):
    ward = payload.get("ward_id")
    notes = payload.get("details")
    if not isinstance(ward, str) or not ward.strip() or not isinstance(notes, str) or not notes.strip():
        raise HTTPException(status_code=422, detail="ward_id and handover details are required.")
    handover = NurseHandover(nurse_id=current_user.id, ward=ward.strip(), notes=notes.strip())
    db.add(handover)
    await db.commit()
    await db.refresh(handover)
    return handover
