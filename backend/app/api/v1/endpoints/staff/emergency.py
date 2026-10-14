from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.emergency import EmergencyCase
from app.models.operations import EmergencyMessage
from app.models.patient import Patient
from app.models.user import User
from app.services.ws_manager import ws_manager

router = APIRouter()
RESPONDER_ROLES = ["emergency", "doctor", "nurse", "staff", "admin", "super_admin"]


class AssignResponder(BaseModel):
    responder_id: int = Field(gt=0)


class MessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class StatusUpdate(BaseModel):
    status: str = Field(pattern="^(acknowledged|en_route|arrived|treating|resolved)$")


@router.get("/active")
async def active_emergencies(
    current_user: User = Depends(deps.check_role(RESPONDER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmergencyCase).where(EmergencyCase.status != "resolved").order_by(EmergencyCase.created_at))
    cases = result.scalars().all()
    response = []
    for case in cases:
        patient = await db.get(Patient, case.patient_id) if case.patient_id is not None else None
        response.append({
            "id": case.id,
            "emergency_id": case.id,
            "patient_id": case.patient_id,
            "patient_name": f"{patient.first_name} {patient.last_name}" if patient else None,
            "status": case.status,
            "priority": case.priority,
            "location": case.location_desc,
            "assigned_staff": case.assigned_staff,
            "created_at": case.created_at,
            "arrival_time": case.arrival_time,
        })
    return {"items": response}


@router.get("/{emergency_id}")
async def emergency_details(
    emergency_id: int,
    current_user: User = Depends(deps.check_role(RESPONDER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    case = await db.get(EmergencyCase, emergency_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Emergency incident not found.")
    patient = await db.get(Patient, case.patient_id) if case.patient_id is not None else None
    user = await db.get(User, patient.user_id) if patient is not None else None
    messages_result = await db.execute(select(EmergencyMessage).where(EmergencyMessage.emergency_id == emergency_id).order_by(EmergencyMessage.created_at))
    messages = messages_result.scalars().all()
    return {
        "id": case.id,
        "patient_id": case.patient_id,
        "patient_name": f"{patient.first_name} {patient.last_name}" if patient else None,
        "blood_group": patient.blood_group if patient else None,
        "allergies": patient.allergies if patient else None,
        "emergency_contact": patient.emergency_contact if patient else None,
        "emergency_contact_name": patient.emergency_contact_name if patient else None,
        "patient_phone": user.phone if user else None,
        "status": case.status,
        "priority": case.priority,
        "location": case.location_desc,
        "description": case.description,
        "assigned_staff": case.assigned_staff,
        "created_at": case.created_at,
        "acknowledged_at": case.acknowledged_at,
        "en_route_at": case.en_route_at,
        "arrived_at": case.arrival_time,
        "messages": [{"id": message.id, "sender_id": message.sender_id, "message": message.message, "created_at": message.created_at} for message in messages],
    }


@router.post("/{emergency_id}/assign")
async def assign_responder(
    emergency_id: int,
    payload: AssignResponder,
    current_user: User = Depends(deps.check_role(RESPONDER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    case = await db.get(EmergencyCase, emergency_id)
    responder = await db.get(User, payload.responder_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Emergency incident not found.")
    if responder is None or not responder.is_active or responder.role not in RESPONDER_ROLES:
        raise HTTPException(status_code=404, detail="Active emergency responder not found.")
    case.assigned_staff = {"user_id": responder.id, "role": responder.role}
    case.status = "staff_assigned"
    case.updated_at = datetime.utcnow()
    case.acknowledged_at = case.acknowledged_at or case.updated_at
    await db.commit()
    payload_out = {"action": "emergency_ack", "emergency_id": case.id, "patient_id": case.patient_id, "responder_id": responder.id, "status": case.status}
    await ws_manager.broadcast_to_room(payload_out, "emergency")
    return payload_out


@router.put("/{emergency_id}/status")
async def update_emergency_status(
    emergency_id: int,
    payload: StatusUpdate,
    current_user: User = Depends(deps.check_role(RESPONDER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    case = await db.get(EmergencyCase, emergency_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Emergency incident not found.")
    transitions = {
        "acknowledged": {"triggered", "staff_assigned"},
        "en_route": {"staff_assigned", "acknowledged", "en_route"},
        "arrived": {"en_route", "arrived"},
        "treating": {"arrived", "treating"},
        "resolved": {"arrived", "treating", "resolved"},
    }
    if case.status not in transitions[payload.status]:
        raise HTTPException(status_code=409, detail=f"Cannot move incident from '{case.status}' to '{payload.status}'.")
    case.status = "staff_assigned" if payload.status == "acknowledged" else payload.status
    case.updated_at = datetime.utcnow()
    if payload.status == "arrived":
        case.arrival_time = datetime.utcnow()
    if payload.status == "en_route":
        case.en_route_at = case.en_route_at or case.updated_at
    if payload.status == "acknowledged":
        case.acknowledged_at = case.acknowledged_at or case.updated_at
    await db.commit()
    event = {"action": "emergency_status", "emergency_id": case.id, "patient_id": case.patient_id, "status": case.status, "updated_at": case.updated_at}
    await ws_manager.broadcast_to_room(event, "emergency")
    if case.patient_id is not None:
        await ws_manager.send_personal_message(event, str(case.patient_id))
    return event


@router.post("/{emergency_id}/message", status_code=201)
async def send_emergency_message(
    emergency_id: int,
    payload: MessageCreate,
    current_user: User = Depends(deps.check_role(RESPONDER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    case = await db.get(EmergencyCase, emergency_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Emergency incident not found.")
    message = EmergencyMessage(emergency_id=case.id, sender_id=current_user.id, message=payload.message.strip())
    db.add(message)
    await db.commit()
    await db.refresh(message)
    event = {"action": "emergency_message", "emergency_id": case.id, "patient_id": case.patient_id, "message": message.message, "sender_id": current_user.id, "created_at": message.created_at}
    await ws_manager.broadcast_to_room(event, "emergency")
    if case.patient_id is not None:
        await ws_manager.send_personal_message(event, str(case.patient_id))
    return event
