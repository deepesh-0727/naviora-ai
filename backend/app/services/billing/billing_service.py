import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.billing import Billing
from app.models.appointment import Appointment
from app.models.doctor import Doctor

logger = logging.getLogger(__name__)

class BillingService:
    async def create_invoice(
        self,
        db: AsyncSession,
        patient_id: int,
        appointment_id: Optional[int] = None,
        additional_items: List[Dict[str, Any]] = None
    ) -> Billing:
        """
        Create a new invoice for a patient.
        Automatically calculates doctor consultation fees if an appointment_id is provided.
        """
        subtotal = 0.0
        items = []

        if appointment_id:
            result = await db.execute(
                select(Appointment).filter(Appointment.id == appointment_id)
            )
            app = result.scalars().first()
            if app:
                doc_result = await db.execute(
                    select(Doctor).filter(Doctor.id == app.doctor_id)
                )
                doctor = doc_result.scalars().first()
                fee = float(doctor.consultation_fee) if doctor and doctor.consultation_fee else 500.0
                subtotal += fee
                items.append({
                    "name": f"Consultation - Dr. {doctor.first_name if doctor else ''} {doctor.last_name if doctor else 'Specialist'}",
                    "quantity": 1,
                    "price": fee
                })

        if additional_items:
            for item in additional_items:
                price = float(item.get("price", 0.0))
                subtotal += price
                items.append(item)

        gst_amount = round(subtotal * 0.18, 2)
        total_amount = round(subtotal + gst_amount, 2)
        items.append({
            "name": "GST (18%)",
            "quantity": 1,
            "price": gst_amount
        })

        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        db_billing = Billing(
            patient_id=patient_id,
            appointment_id=appointment_id,
            amount=total_amount,
            status="pending",
            invoice_number=invoice_number,
            items=items
        )
        db.add(db_billing)
        await db.commit()
        await db.refresh(db_billing)

        return db_billing

    async def update_payment_status(
        self,
        db: AsyncSession,
        billing_id: int,
        status: str,
        payment_method: str = "UPI",
        transaction_id: str = None
    ) -> Optional[Billing]:
        result = await db.execute(select(Billing).filter(Billing.id == billing_id))
        billing = result.scalars().first()

        if billing:
            billing.status = status
            billing.payment_method = payment_method
            billing.transaction_id = transaction_id
            billing.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(billing)
        return billing

billing_service = BillingService()
