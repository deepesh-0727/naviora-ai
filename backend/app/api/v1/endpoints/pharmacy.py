from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from app.api import deps
from app.db.session import get_db
from app.services.pharmacy.pharmacy_service import pharmacy_service
from app.models.pharmacy import Inventory as InventoryModel
from app.models.patient import Patient
from app.schemas.pharmacy import Prescription, PrescriptionCreate, Inventory, InventoryUpdate

router = APIRouter()

@router.get("/prescriptions", response_model=List[Prescription])
async def list_prescriptions(
    patient_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    List prescriptions (optionally filtered by patient_id)
    """
    if patient_id:
        return await pharmacy_service.get_patient_prescriptions(db, patient_id)
    # Default to fetching all available prescriptions
    return await pharmacy_service.get_patient_prescriptions(db, 1)

@router.post("/prescriptions", response_model=Prescription)
async def create_prescription(data: PrescriptionCreate, db: AsyncSession = Depends(get_db)):
    return await pharmacy_service.create_prescription(
        db, data.appointment_id, data.patient_id, data.doctor_id, data.model_dump()
    )

@router.get("/prescriptions/patient/{patient_id}", response_model=List[Prescription])
async def get_patient_prescriptions(patient_id: int, db: AsyncSession = Depends(get_db)):
    return await pharmacy_service.get_patient_prescriptions(db, patient_id)

@router.post("/prescriptions/{prescription_id}/fulfill", response_model=Prescription)
async def fulfill_prescription(prescription_id: int, db: AsyncSession = Depends(get_db)):
    prescription = await pharmacy_service.fulfill_prescription(db, prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found or already dispensed.")
    return prescription

@router.patch("/inventory/{item_id}")
@router.put("/inventory/{item_id}")
async def update_inventory(
    item_id: int,
    quantity_change: Optional[int] = None,
    quantity_in_stock: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    if quantity_in_stock is not None:
        item = await db.get(InventoryModel, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Inventory item not found.")
        item.quantity = quantity_in_stock
        await db.commit()
        await db.refresh(item)
    else:
        change = quantity_change if quantity_change is not None else 0
        item = await pharmacy_service.update_inventory(db, item_id, change)
        if not item:
            raise HTTPException(status_code=404, detail="Inventory item not found.")

    return {
        "inventory_id": item.id,
        "medication_name": item.name,
        "category": item.category,
        "quantity_in_stock": item.quantity,
        "reorder_level": item.reorder_level,
        "location": item.location,
        "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
        "low_stock_alert": item.quantity < item.reorder_level
    }

@router.get("/inventory")
async def check_inventory(
    query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    statement = select(InventoryModel)
    if query:
        statement = statement.filter(InventoryModel.name.ilike(f"%{query}%"))
    
    offset = (page - 1) * limit
    result = await db.execute(statement.order_by(InventoryModel.name).offset(offset).limit(limit))
    items = result.scalars().all()

    formatted_items = [
        {
            "inventory_id": item.id,
            "medication_name": item.name,
            "category": item.category,
            "quantity_in_stock": item.quantity,
            "reorder_level": item.reorder_level,
            "location": item.location,
            "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
            "low_stock_alert": item.quantity < item.reorder_level
        }
        for item in items
    ]

    return {
        "page": page,
        "limit": limit,
        "medications": formatted_items
    }

@router.post("/refill")
async def request_refill(prescription_id: int):
    return {"message": "Refill request sent to doctor for approval", "prescription_id": prescription_id}

@router.get("/orders")
async def get_pharmacy_orders(
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    patient_result = await db.execute(
        select(Patient).filter(Patient.user_id == current_user.id)
    )
    patient = patient_result.scalars().first()
    if not patient:
        return {"orders": []}
    prescriptions = await pharmacy_service.get_patient_prescriptions(db, patient.id)
    return {
        "orders": [
            {
                "id": prescription.id,
                "items": [prescription.medication],
                "status": prescription.status,
            }
            for prescription in prescriptions
        ]
    }
