from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.communication import Notification
from app.models.patient import Patient
from app.models.pharmacy import Inventory, Prescription
from app.models.user import User

router = APIRouter()
PHARMACY_ROLES = ["pharmacy", "admin", "super_admin"]


class InteractionCheck(BaseModel):
    prescription_id: int = Field(gt=0)
    patient_id: int = Field(gt=0)


class PickupNotification(BaseModel):
    prescription_id: int = Field(gt=0)
    patient_id: int = Field(gt=0)


@router.get("/prescriptions")
async def prescription_queue(
    current_user: User = Depends(deps.check_role(PHARMACY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prescription)
        .where(Prescription.status.in_(["pending", "active", "refill_requested"]))
        .order_by(Prescription.created_at)
    )
    return {"items": result.scalars().all()}


@router.get("/inventory")
async def inventory(
    low_stock: bool = False,
    barcode: str | None = None,
    current_user: User = Depends(deps.check_role(PHARMACY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    query = select(Inventory)
    if low_stock:
        query = query.where(Inventory.quantity <= Inventory.reorder_level)
    if barcode:
        query = query.where(func.lower(Inventory.name).contains(barcode.strip().lower()))
    result = await db.execute(query.order_by(Inventory.name))
    return {"items": result.scalars().all()}


@router.post("/dispense/{prescription_id}")
async def dispense(
    prescription_id: int,
    current_user: User = Depends(deps.check_role(PHARMACY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Prescription).where(Prescription.id == prescription_id).with_for_update())
    prescription = result.scalar_one_or_none()
    if prescription is None:
        raise HTTPException(status_code=404, detail="Prescription not found.")
    if prescription.status not in {"pending", "active"}:
        raise HTTPException(status_code=409, detail="Prescription is not eligible for dispensing.")
    stock_result = await db.execute(select(Inventory).where(func.lower(Inventory.name) == prescription.medication.lower()).with_for_update())
    stock = stock_result.scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=409, detail="The prescribed medication is not present in inventory.")
    if stock.quantity <= 0:
        raise HTTPException(status_code=409, detail="Medication is out of stock.")
    stock.quantity -= 1
    stock.updated_at = datetime.utcnow()
    prescription.status = "dispensed"
    prescription.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(prescription)
    return {"prescription_id": prescription.id, "status": prescription.status, "remaining_stock": stock.quantity}


@router.post("/interaction-check")
async def interaction_check(
    payload: InteractionCheck,
    current_user: User = Depends(deps.check_role(PHARMACY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    prescription = await db.get(Prescription, payload.prescription_id)
    if prescription is None or prescription.patient_id != payload.patient_id:
        raise HTTPException(status_code=404, detail="Prescription not found for this patient.")
    result = await db.execute(
        select(Prescription).where(
            Prescription.patient_id == payload.patient_id,
            Prescription.id != payload.prescription_id,
            Prescription.status.in_(["active", "pending"]),
            func.lower(Prescription.medication) == prescription.medication.lower(),
        )
    )
    matching = result.scalars().all()
    return {
        "prescription_id": prescription.id,
        "checked_medication": prescription.medication,
        "interactions": [{"type": "duplicate_medication", "prescription_id": item.id, "medication": item.medication} for item in matching],
    }


@router.post("/refill/{prescription_id}/approve")
async def approve_refill(
    prescription_id: int,
    current_user: User = Depends(deps.check_role(PHARMACY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    prescription = await db.get(Prescription, prescription_id)
    if prescription is None:
        raise HTTPException(status_code=404, detail="Prescription not found.")
    if prescription.status != "refill_requested":
        raise HTTPException(status_code=409, detail="Prescription has no pending refill request.")
    prescription.status = "active"
    prescription.updated_at = datetime.utcnow()
    await db.commit()
    return {"prescription_id": prescription.id, "status": prescription.status}


@router.post("/notify-pickup")
async def notify_pickup(
    payload: PickupNotification,
    current_user: User = Depends(deps.check_role(PHARMACY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    prescription = await db.get(Prescription, payload.prescription_id)
    patient = await db.get(Patient, payload.patient_id)
    if prescription is None or patient is None or prescription.patient_id != patient.id:
        raise HTTPException(status_code=404, detail="Prescription or patient not found.")
    notification = Notification(
        user_id=patient.user_id,
        type="push",
        channel="patient_app",
        title="Prescription ready for pickup",
        message=f"Your prescription for {prescription.medication} is ready for pickup.",
        data={"prescription_id": prescription.id},
        priority="normal",
        is_read=False,
        is_delivered=False,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return {"notification_id": notification.id, "status": "queued"}
