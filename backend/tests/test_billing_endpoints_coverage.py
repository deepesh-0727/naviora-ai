import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import String, select

from app.core.security import create_access_token
from app.models.billing import Billing
from app.models.doctor import Department, Doctor
from app.models.patient import Patient
from app.models.user import User


@pytest.fixture
async def billing_api_context(db_session, monkeypatch):
    from app.api.v1.endpoints import billing as billing_module

    monkeypatch.setattr(Department.__table__.c.location, "type", String())
    patient_user = User(phone="9800009901", email="billing.patient@tests.example", password_hash="hash", role="patient")
    doctor_user = User(phone="9800009902", email="billing.doctor@tests.example", password_hash="hash", role="doctor")
    department = Department(name="Billing API Tests", floor=1, building="A", wing="East", phone="333", email="billing-api@tests.example")
    db_session.add_all([patient_user, doctor_user, department])
    await db_session.flush()
    patient = Patient(user_id=patient_user.id, first_name="Bill", last_name="Patient", date_of_birth=datetime(1990, 1, 1), gender="unknown", emergency_contact="", emergency_contact_name="")
    doctor = Doctor(user_id=doctor_user.id, first_name="Bill", last_name="Doctor", specialization="General", department_id=department.id, license_number="BILLING-API-DOC", years_of_experience=5, consultation_fee=1000)
    db_session.add_all([patient, doctor])
    await db_session.flush()
    invoice = Billing(patient_id=patient.id, amount=1180, status="pending", invoice_number="INV-COVERAGE-1", items=[{"name": "Consultation", "quantity": 1, "price": 1000}])
    paid_invoice = Billing(patient_id=patient.id, amount=500, status="paid", invoice_number="INV-COVERAGE-PAID", items=[])
    db_session.add_all([invoice, paid_invoice])
    await db_session.commit()
    monkeypatch.setattr(billing_module.payment_service, "create_order", AsyncMock(return_value={"id": "order_test", "currency": "INR"}))
    return {"patient_user": patient_user, "patient": patient, "doctor": doctor, "invoice": invoice, "paid_invoice": paid_invoice,
            "headers": {"Authorization": f"Bearer {create_access_token(subject=patient_user.id, claims={'role': 'patient'})}"}}


@pytest.mark.asyncio
async def test_invoice_listing_and_history_are_patient_scoped(async_client: AsyncClient, billing_api_context, db_session):
    ctx = billing_api_context
    invoices = await async_client.get("/api/v1/billing/invoices", headers=ctx["headers"])
    history = await async_client.get("/api/v1/billing/history", headers=ctx["headers"])
    missing_user = User(phone="9800009903", email="billing.no.profile@tests.example", password_hash="hash", role="patient")
    db_session.add(missing_user)
    await db_session.commit()
    missing_headers = {"Authorization": f"Bearer {create_access_token(subject=missing_user.id, claims={'role': 'patient'})}"}
    no_profile = await async_client.get("/api/v1/billing/invoices", headers=missing_headers)
    assert invoices.status_code == 200 and {row["invoice_number"] for row in invoices.json()} == {"INV-COVERAGE-1", "INV-COVERAGE-PAID"}
    assert len(history.json()["history"]) == 2 and no_profile.json() == []


@pytest.mark.asyncio
async def test_create_invoice_and_payment_paths(async_client: AsyncClient, billing_api_context, db_session):
    ctx = billing_api_context
    created = await async_client.post("/api/v1/billing/invoices", headers=ctx["headers"], json={"patient_id": ctx["patient"].id, "additional_items": [{"name": "Lab", "quantity": 1, "price": 200}]})
    invoice_id = created.json()["id"]
    pay = await async_client.patch(f"/api/v1/billing/invoices/{invoice_id}/pay?payment_method=upi&transaction_id=txn-100", headers=ctx["headers"])
    await db_session.refresh(ctx["invoice"])
    payment = await async_client.post("/api/v1/billing/payment", headers=ctx["headers"], json={"invoice_id": ctx["invoice"].id, "payment_method": "card", "transaction_id": "txn-200"})
    missing = await async_client.patch("/api/v1/billing/invoices/99999/pay?payment_method=upi&transaction_id=missing", headers=ctx["headers"])
    assert created.status_code == 200 and created.json()["amount"] == "236.00"
    assert pay.status_code == 200 and pay.json()["status"] == "paid"
    assert payment.json() == {"status": "success", "message": f"Payment of invoice {ctx['invoice'].id} processed successfully.", "transaction_id": "txn-200"}
    assert ctx["invoice"].status == "paid" and ctx["invoice"].transaction_id == "txn-200"
    assert (missing.status_code, missing.json()["detail"]) == (404, "Invoice not found.")


@pytest.mark.asyncio
async def test_invoice_detail_and_estimate(async_client: AsyncClient, billing_api_context):
    ctx = billing_api_context
    detail = await async_client.get(f"/api/v1/billing/invoices/{ctx['invoice'].id}", headers=ctx["headers"])
    missing = await async_client.get("/api/v1/billing/invoices/99999", headers=ctx["headers"])
    estimate = await async_client.post("/api/v1/billing/estimate", headers=ctx["headers"], json={"doctor_id": ctx["doctor"].id})
    missing_doctor = await async_client.post("/api/v1/billing/estimate", headers=ctx["headers"], json={"doctor_id": 99999})
    assert detail.json()["invoice_number"] == "INV-COVERAGE-1"
    assert (missing.status_code, missing.json()["detail"]) == (404, "Invoice not found")
    assert estimate.json()["subtotal"] == 1000 and estimate.json()["gst_amount"] == 180
    assert (missing_doctor.status_code, missing_doctor.json()["detail"]) == (404, "Doctor not found.")


@pytest.mark.asyncio
async def test_razorpay_order_and_paid_invoice_conflict(async_client: AsyncClient, billing_api_context):
    ctx = billing_api_context
    order = await async_client.post("/api/v1/billing/create-razorpay-order", headers=ctx["headers"], json={"invoice_id": ctx["invoice"].id})
    paid = await async_client.post("/api/v1/billing/create-razorpay-order", headers=ctx["headers"], json={"invoice_id": ctx["paid_invoice"].id})
    missing = await async_client.post("/api/v1/billing/create-razorpay-order", headers=ctx["headers"], json={"invoice_id": 99999})
    assert order.json() == {"order_id": "order_test", "amount": 1180, "currency": "INR", "invoice_id": ctx["invoice"].id, "invoice_number": "INV-COVERAGE-1"}
    assert (paid.status_code, paid.json()["detail"]) == (400, "Invoice already paid")
    assert (missing.status_code, missing.json()["detail"]) == (404, "Invoice not found")


@pytest.mark.asyncio
async def test_razorpay_webhook_validates_signature_and_records_capture(async_client: AsyncClient, billing_api_context, db_session, monkeypatch):
    from app.api.v1.endpoints import billing as billing_module

    ctx = billing_api_context
    monkeypatch.setattr(billing_module.settings, "RAZORPAY_WEBHOOK_SECRET", "unit-test-webhook-secret")
    body = json.dumps({"event": "payment.captured", "payload": {"payment": {"entity": {
        "order_id": "order-123", "id": "pay-123", "amount": 118000, "method": "upi", "receipt": "INV-COVERAGE-1",
    }}}}).encode()
    invalid = await async_client.post("/api/v1/billing/webhook", content=body, headers={**ctx["headers"], "x-razorpay-signature": "invalid"})
    signature = hmac.new(b"unit-test-webhook-secret", body, hashlib.sha256).hexdigest()
    captured = await async_client.post("/api/v1/billing/webhook", content=body, headers={**ctx["headers"], "x-razorpay-signature": signature})
    await db_session.refresh(ctx["invoice"])
    invalid_json_body = b"not json"
    invalid_json_signature = hmac.new(b"unit-test-webhook-secret", invalid_json_body, hashlib.sha256).hexdigest()
    bad_json = await async_client.post("/api/v1/billing/webhook", content=invalid_json_body, headers={**ctx["headers"], "x-razorpay-signature": invalid_json_signature})
    assert (invalid.status_code, invalid.json()["detail"]) == (400, "Invalid webhook signature")
    assert captured.json() == {"status": "acknowledged", "event": "payment.captured"}
    assert ctx["invoice"].status == "paid" and ctx["invoice"].transaction_id == "pay-123"
    assert (bad_json.status_code, bad_json.json()["detail"]) == (400, "Invalid JSON payload")
