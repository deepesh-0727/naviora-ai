from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.services.emergency_service import emergency_service
from app.services.location_service import location_service
from sqlalchemy.future import select
from app.models.emergency import EmergencyCase
from app.api import deps
from app.models.patient import Patient
from app.models.user import User

router = APIRouter()

class SOSRequest(BaseModel):
    location: str
    description: Optional[str] = ""

@router.post("/trigger")
@router.post("/sos")
async def trigger_sos(
    request: SOSRequest,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger an emergency SOS.
    """
    patient_id = None
    if current_user.role == "patient":
        patient_result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = patient_result.scalars().first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found.")
        patient_id = patient.id
    result = await emergency_service.trigger_sos(
        db,
        patient_id=patient_id,
        location=request.location,
        description=request.description
    )
    return result

@router.post("/respond/{emergency_id}")
async def respond_to_emergency(
    emergency_id: int,
    current_user: User = Depends(deps.check_role(["doctor", "nurse", "staff", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Staff member accepts an emergency case.
    """
    try:
        emergency = await emergency_service.assign_staff(db, emergency_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency case not found")
    return {
        "emergency_id": emergency.id,
        "status": emergency.status,
        "staff_id": current_user.id,
    }

@router.get("/status/{id}")
async def get_emergency_status(
    id: int,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmergencyCase).filter(EmergencyCase.id == id))
    emergency = result.scalars().first()
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency case not found")
    if current_user.role == "patient":
        patient_result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = patient_result.scalars().first()
        if not patient or emergency.patient_id != patient.id:
            raise HTTPException(status_code=403, detail="You can only view your own emergency.")
    elif current_user.role not in {"doctor", "nurse", "staff", "admin"}:
        raise HTTPException(status_code=403, detail="You are not authorized to view emergencies.")
    return {
        "id": emergency.id,
        "status": emergency.status,
        "priority": emergency.priority,
        "location": emergency.location_desc,
        "assigned_staff": emergency.assigned_staff,
        "arrival_time": emergency.arrival_time,
    }

@router.get("/active")
async def get_active_emergencies(
    current_user: User = Depends(deps.check_role(["doctor", "nurse", "staff", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmergencyCase)
        .where(EmergencyCase.status != "resolved")
        .order_by(EmergencyCase.created_at.desc())
    )
    return {
        "items": [
            {
                "id": case.id,
                "patient_id": case.patient_id,
                "status": case.status,
                "priority": case.priority,
                "location": case.location_desc,
                "description": case.description,
                "assigned_staff": case.assigned_staff,
                "arrival_time": case.arrival_time,
                "created_at": case.created_at,
            }
            for case in result.scalars().all()
        ]
    }

@router.put("/resolve/{id}")
async def resolve_emergency(
    id: int,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    emergency = await db.get(EmergencyCase, id)
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency case not found")
    if current_user.role == "patient":
        patient_result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = patient_result.scalars().first()
        if not patient or emergency.patient_id != patient.id:
            raise HTTPException(status_code=403, detail="You can only resolve your own emergency.")
    elif current_user.role not in {"doctor", "nurse", "staff", "admin"}:
        raise HTTPException(status_code=403, detail="You are not authorized to resolve emergencies.")
    emergency.status = "resolved"
    await db.commit()
    await db.refresh(emergency)
    return {"id": emergency.id, "status": emergency.status}

@router.get("/nearby-staff")
async def get_nearby_staff(
    latitude: float,
    longitude: float,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top 3 nearest staff within 100 meters using GPS coordinates.
    """
    nearest_staff = await location_service.get_nearest_staff_by_coords(
        db, lat=latitude, lon=longitude, max_distance_meters=100.0, limit=3
    )
    return {"staff": nearest_staff}

@router.post("/staff-acknowledge")
async def acknowledge_emergency(
    emergency_id: int,
    current_user: User = Depends(deps.check_role(["doctor", "nurse", "staff", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    try:
        emergency = await emergency_service.assign_staff(db, emergency_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency case not found.")
    return {"emergency_id": emergency.id, "status": emergency.status, "staff_id": current_user.id}

@router.put("/staff-arrived")
async def staff_arrived(
    emergency_id: int,
    current_user: User = Depends(deps.check_role(["doctor", "nurse", "staff", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    emergency = await db.get(EmergencyCase, emergency_id)
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency case not found.")
    if emergency.status == "resolved":
        raise HTTPException(status_code=409, detail="Resolved emergencies cannot be marked as arrived.")
    if (emergency.assigned_staff or {}).get("primary_staff_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Only the assigned responder can mark arrival.")
    emergency.arrival_time = datetime.utcnow()
    emergency.status = "staff_arrived"
    await db.commit()
    return {"emergency_id": emergency.id, "status": emergency.status, "arrival_time": emergency.arrival_time}
