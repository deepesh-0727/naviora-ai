import hmac
import hashlib
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from pydantic import BaseModel

from app.api import deps
from app.core.config import settings
from app.db.session import get_db
from app.services.billing.billing_service import billing_service
from app.services.payment.payment_service import payment_service
from app.schemas.billing import Billing, BillingCreate, BillingUpdate
from app.models.billing import Billing as BillingModel
from app.models.patient import Patient
from app.models.hospital import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter()

class PaymentRequest(BaseModel):
    invoice_id: int
    payment_method: str
    transaction_id: str

@router.get("/invoices")
async def list_invoices(
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user invoices
    """
    patient_result = await db.execute(
        select(Patient).filter(Patient.user_id == current_user.id)
    )
    patient = patient_result.scalars().first()
    if not patient:
        return []
    result = await db.execute(
        select(BillingModel)
        .filter(BillingModel.patient_id == patient.id)
        .order_by(BillingModel.created_at.desc())
    )
    return result.scalars().all()

@router.post("/invoices", response_model=Billing)
async def create_invoice(data: BillingCreate, db: AsyncSession = Depends(get_db)):
    return await billing_service.create_invoice(
        db, data.patient_id, data.appointment_id, data.additional_items
    )

@router.post("/payment")
async def make_payment(payment: PaymentRequest, db: AsyncSession = Depends(get_db)):
    """
    Process a digital payment for an invoice
    """
    billing = await billing_service.update_payment_status(
        db, payment.invoice_id, "paid", payment.payment_method, payment.transaction_id
    )
    return {
        "status": "success",
        "message": f"Payment of invoice {payment.invoice_id} processed successfully.",
        "transaction_id": payment.transaction_id
    }

@router.patch("/invoices/{billing_id}/pay", response_model=Billing)
async def pay_invoice(
    billing_id: int,
    payment_method: str,
    transaction_id: str,
    db: AsyncSession = Depends(get_db)
):
    billing = await billing_service.update_payment_status(
        db, billing_id, "paid", payment_method, transaction_id
    )
    if not billing:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return billing

@router.get("/invoices/{id}")
async def get_invoice_details(id: int, db: AsyncSession = Depends(get_db)):
    billing = await db.get(BillingModel, id)
    if not billing:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return billing

@router.get("/history")
async def get_billing_history(
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    patient_result = await db.execute(
        select(Patient).filter(Patient.user_id == current_user.id)
    )
    patient = patient_result.scalars().first()
    if not patient:
        return {"history": []}
    result = await db.execute(
        select(BillingModel)
        .filter(BillingModel.patient_id == patient.id)
        .order_by(BillingModel.created_at.desc())
    )
    return {"history": result.scalars().all()}

from app.schemas.billing import Billing, BillingCreate, BillingUpdate, BillingEstimate, BillingEstimateRequest, ItemDetail
from app.models.doctor import Doctor
from app.models.pharmacy import Inventory as InventoryModel

@router.post("/estimate", response_model=BillingEstimate)
async def get_bill_estimate(
    request: Optional[BillingEstimateRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    req = request or BillingEstimateRequest()
    
    # 1. Consultation fee
    consultation_fee = 0.0
    if req.doctor_id:
        doc_res = await db.execute(select(Doctor).filter(Doctor.id == req.doctor_id))
        doc = doc_res.scalars().first()
        if not doc:
            raise HTTPException(status_code=404, detail="Doctor not found.")
        consultation_fee = float(doc.consultation_fee or 0)

    from app.models.lab_service import LabService
    
    # 2. Lab test fees
    lab_fees = []
    if req.lab_test_ids:
        for lab_id in req.lab_test_ids:
            lab_res = await db.execute(select(LabService).filter(LabService.id == lab_id))
            lab = lab_res.scalars().first()
            if not lab:
                raise HTTPException(status_code=404, detail=f"Lab test {lab_id} not found.")
            lab_fees.append(ItemDetail(name=lab.name, amount=float(lab.price)))

    # 3. Medication costs
    medication_costs = []
    if req.medication_ids:
        for med_id in req.medication_ids:
            med_res = await db.execute(select(InventoryModel).filter(InventoryModel.id == med_id))
            med = med_res.scalars().first()
            if not med:
                raise HTTPException(status_code=404, detail=f"Medication {med_id} not found.")
            # Inventory currently stores stock, not a sale price.

    lab_total = sum(item.amount for item in lab_fees)
    med_total = sum(item.amount for item in medication_costs)

    subtotal = consultation_fee + lab_total + med_total
    gst_amount = round(subtotal * 0.18, 2)
    total_amount = round(subtotal + gst_amount, 2)

    return BillingEstimate(
        consultation_fee=consultation_fee,
        lab_fees=lab_fees,
        medication_costs=medication_costs,
        subtotal=subtotal,
        gst_amount=gst_amount,
        total_amount=total_amount,
        currency="INR"
    )


# ── Razorpay: Create Order ────────────────────────────────────────────────────

class CreateRazorpayOrderRequest(BaseModel):
    invoice_id: int
    amount: Optional[float] = None  # override amount if needed


@router.post("/create-razorpay-order")
async def create_razorpay_order(
    body: CreateRazorpayOrderRequest,
    current_user=Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Razorpay payment order for a given invoice.
    Returns order_id which the frontend passes to the Razorpay SDK.
    """
    billing = await db.get(BillingModel, body.invoice_id)
    if not billing:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if billing.status == "paid":
        raise HTTPException(status_code=400, detail="Invoice already paid")

    amount = body.amount or float(billing.amount)
    receipt = billing.invoice_number

    order = await payment_service.create_order(
        amount_in_inr=amount, receipt=receipt
    )
    return {
        "order_id": order["id"],
        "amount": amount,
        "currency": order.get("currency", "INR"),
        "invoice_id": body.invoice_id,
        "invoice_number": billing.invoice_number,
    }


# ── Razorpay: Payment Webhook ─────────────────────────────────────────────────

@router.post("/webhook", include_in_schema=False)
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Razorpay will POST signed events here.
    Configure in Razorpay Dashboard → Webhooks → https://<your-domain>/api/v1/billing/webhook
    Events handled: payment.captured
    """
    body_bytes = await request.body()
    received_signature = request.headers.get("x-razorpay-signature", "")
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    # ── Verify signature ──────────────────────────────────────────────────────
    if webhook_secret:
        expected = hmac.new(
            webhook_secret.encode("utf-8"),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, received_signature):
            logger.warning("[Webhook] Invalid Razorpay signature — rejecting")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        logger.warning("[Webhook] RAZORPAY_WEBHOOK_SECRET not set — skipping verification (unsafe)")

    import json
    try:
        payload = json.loads(body_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event")
    logger.info(f"[Webhook] Received event: {event}")

    # ── Handle payment.captured ───────────────────────────────────────────────
    if event == "payment.captured":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id     = payment_entity.get("order_id")
        payment_id   = payment_entity.get("id")
        amount_paise = payment_entity.get("amount", 0)
        method       = payment_entity.get("method", "unknown")
        email        = payment_entity.get("email", "")

        # Find matching invoice by Razorpay order_id stored in transaction_id temporarily
        # or match by amount (simplest approach since we store receipt=invoice_number)
        receipt_id = payment_entity.get("description") or payment_entity.get("receipt")
        if receipt_id:
            result = await db.execute(
                select(BillingModel).filter(BillingModel.invoice_number == receipt_id)
            )
            billing = result.scalars().first()
            if billing and billing.status != "paid":
                billing.status = "paid"
                billing.payment_method = method.upper()
                billing.transaction_id = payment_id
                db.add(billing)

                # Write audit log
                audit = AuditLog(
                    user_id=billing.patient_id,
                    action="PAYMENT_CAPTURED",
                    resource="billing",
                    resource_id=billing.id,
                    details=f"Razorpay payment captured. payment_id={payment_id} order_id={order_id} amount_paise={amount_paise}"
                )
                db.add(audit)
                await db.commit()
                logger.info(f"[Webhook] Invoice {billing.invoice_number} marked PAID via {method}")
            else:
                logger.warning(f"[Webhook] No pending invoice found for receipt={receipt_id}")

    # Always return 200 to acknowledge receipt
    return {"status": "acknowledged", "event": event}
