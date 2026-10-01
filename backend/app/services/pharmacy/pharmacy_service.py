import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from app.models.pharmacy import Prescription, Inventory
from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)

class PharmacyService:
    async def create_prescription(
        self,
        db: AsyncSession,
        appointment_id: int,
        patient_id: int,
        doctor_id: int,
        medication_data: Dict[str, Any]
    ) -> Prescription:
        """
        Create a new prescription for a patient.
        """
        db_prescription = Prescription(
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            medication=medication_data.get("medication"),
            dosage=medication_data.get("dosage"),
            frequency=medication_data.get("frequency"),
            duration=medication_data.get("duration"),
            instructions=medication_data.get("instructions"),
            status="active"
        )
        db.add(db_prescription)
        await db.commit()
        await db.refresh(db_prescription)

        # Notify patient
        # Note: We'd need to fetch the patient's user_id if we want to send a personal message.
        # For now, let's assume the caller handles specific notifications or we add user_id fetch here.

        return db_prescription

    async def get_patient_prescriptions(self, db: AsyncSession, patient_id: int) -> List[Prescription]:
        result = await db.execute(select(Prescription).filter(Prescription.patient_id == patient_id))
        return result.scalars().all()

    async def fulfill_prescription(self, db: AsyncSession, prescription_id: int) -> Optional[Prescription]:
        """
        Mark a prescription as dispensed and update inventory.
        """
        result = await db.execute(select(Prescription).filter(Prescription.id == prescription_id))
        prescription = result.scalars().first()

        if not prescription or prescription.status != "active":
            return None

        # Try to deduct from inventory
        inventory_result = await db.execute(
            select(Inventory).filter(Inventory.name.ilike(f"%{prescription.medication}%"))
        )
        item = inventory_result.scalars().first()

        if item and item.quantity > 0:
            item.quantity -= 1
            if item.quantity <= item.reorder_level:
                await ws_manager.broadcast_to_room(
                    {
                        "type": "inventory_alert",
                        "item": item.name,
                        "quantity": item.quantity,
                        "message": f"Low stock alert for {item.name}"
                    },
                    "pharmacy_staff"
                )

        prescription.status = "dispensed"
        prescription.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(prescription)

        return prescription

    async def update_inventory(self, db: AsyncSession, item_id: int, quantity_change: int) -> Optional[Inventory]:
        result = await db.execute(select(Inventory).filter(Inventory.id == item_id))
        item = result.scalars().first()

        if item:
            item.quantity += quantity_change
            item.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(item)
        return item

pharmacy_service = PharmacyService()
