from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.queue import QueueEntry
from app.models.user import User
from app.services.ws_manager import ws_manager

router = APIRouter()


class QueueStatusUpdate(BaseModel):
    status: str = Field(pattern="^(check_in|in_room|treating|completed)$")


class QueueReorder(BaseModel):
    appointment_ids: list[int] = Field(min_length=1)


async def _doctor_owns(db: AsyncSession, user: User, appointment: Appointment) -> None:
    if user.role != "doctor":
        return
    result = await db.execute(select(Doctor.id).where(Doctor.user_id == user.id))
    doctor_id = result.scalar_one_or_none()
    if doctor_id is None or appointment.doctor_id != doctor_id:
        raise HTTPException(status_code=403, detail="You can only update your own queue.")


@router.put("/{appointment_id}/status")
async def update_queue_status(
    appointment_id: int,
    update: QueueStatusUpdate,
    current_user: User = Depends(deps.check_role(["doctor", "nurse", "staff"])),
    db: AsyncSession = Depends(get_db),
):
    appointment = await db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Queue appointment not found.")
    await _doctor_owns(db, current_user, appointment)
    if appointment.status not in {"check_in", "treating"}:
        raise HTTPException(status_code=409, detail="Appointment is not in the active queue.")
    appointment.status = "treating" if update.status == "in_room" else update.status
    if update.status == "completed":
        appointment.actual_time = datetime.utcnow()
        appointment.queue_position = 0
    queue_result = await db.execute(select(QueueEntry).where(QueueEntry.appointment_id == appointment_id))
    queue_entry = queue_result.scalar_one_or_none()
    if queue_entry is not None:
        queue_entry.status = "served" if update.status == "completed" else update.status
        if update.status == "completed":
            queue_entry.served_at = datetime.utcnow()
    if update.status == "completed":
        from app.services.feedback_scheduler import schedule_feedback_reminder
        await schedule_feedback_reminder(db, appointment)
    await db.commit()
    await db.refresh(appointment)
    payload = {"appointment_id": appointment.id, "doctor_id": appointment.doctor_id, "patient_id": appointment.patient_id, "status": appointment.status, "queue_position": appointment.queue_position}
    await ws_manager.broadcast_event(f"doctor:{appointment.doctor_id}", "queue_update", payload)
    await ws_manager.broadcast_event(f"patient:{appointment.patient_id}", "queue_update", payload)
    return {"id": appointment.id, "status": appointment.status, "queue_position": appointment.queue_position}


@router.put("/reorder")
async def reorder_queue(
    reorder: QueueReorder,
    current_user: User = Depends(deps.check_role(["doctor", "nurse", "staff"])),
    db: AsyncSession = Depends(get_db),
):
    if len(set(reorder.appointment_ids)) != len(reorder.appointment_ids):
        raise HTTPException(status_code=422, detail="Appointment IDs must be unique.")
    result = await db.execute(select(Appointment).where(Appointment.id.in_(reorder.appointment_ids)))
    appointments = result.scalars().all()
    if len(appointments) != len(reorder.appointment_ids) or any(item.status not in {"check_in", "treating"} for item in appointments):
        raise HTTPException(status_code=409, detail="The requested queue does not match active appointments.")
    doctor_ids = {item.doctor_id for item in appointments}
    if len(doctor_ids) != 1:
        raise HTTPException(status_code=422, detail="A queue reorder must target one doctor.")
    doctor_id = next(iter(doctor_ids))
    if current_user.role == "doctor":
        owned = await db.scalar(select(Doctor.id).where(Doctor.user_id == current_user.id, Doctor.id == doctor_id))
        if owned is None:
            raise HTTPException(status_code=403, detail="You can only reorder your own queue.")
    by_id = {item.id: item for item in appointments}
    queue_result = await db.execute(select(QueueEntry).where(QueueEntry.appointment_id.in_(reorder.appointment_ids)))
    queue_entries = {item.appointment_id: item for item in queue_result.scalars().all()}
    for position, appointment_id in enumerate(reorder.appointment_ids, start=1):
        by_id[appointment_id].queue_position = position
        if appointment_id in queue_entries:
            queue_entries[appointment_id].position = position
    await db.commit()
    payload = {"doctor_id": doctor_id, "appointment_ids": reorder.appointment_ids}
    await ws_manager.broadcast_event(f"doctor:{doctor_id}", "queue_update", payload)
    for appointment in appointments:
        await ws_manager.broadcast_event(f"patient:{appointment.patient_id}", "queue_update", payload)
    return {"doctor_id": doctor_id, "appointment_ids": reorder.appointment_ids}


@router.post("/{appointment_id}/no-show")
async def mark_no_show(
    appointment_id: int,
    current_user: User = Depends(deps.check_role(["doctor", "nurse", "staff"])),
    db: AsyncSession = Depends(get_db),
):
    appointment = await db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Queue appointment not found.")
    await _doctor_owns(db, current_user, appointment)
    if appointment.status not in {"check_in", "treating"}:
        raise HTTPException(status_code=409, detail="Appointment is not in the active queue.")
    appointment.status = "no_show"
    appointment.queue_position = 0
    queue_result = await db.execute(select(QueueEntry).where(QueueEntry.appointment_id == appointment_id))
    queue_entry = queue_result.scalar_one_or_none()
    if queue_entry is not None:
        queue_entry.status = "no_show"
    await db.commit()
    payload = {"appointment_id": appointment.id, "doctor_id": appointment.doctor_id, "patient_id": appointment.patient_id, "status": "no_show"}
    await ws_manager.broadcast_event(f"doctor:{appointment.doctor_id}", "queue_update", payload)
    await ws_manager.broadcast_event(f"patient:{appointment.patient_id}", "queue_update", payload)
    return {"id": appointment.id, "status": appointment.status}
