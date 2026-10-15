import os
from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.services import otp_service as otp_module


@pytest.mark.asyncio
async def test_patient_register_login_book_check_queue_and_cancel(async_client, hospital_actors, deterministic_appointment_time):
    registration = {
        "phone": "+919800009101",
        "email": "patient.journey@tests.example",
        "first_name": "Journey",
        "last_name": "Patient",
        "password": "JourneyPass!901",
        "date_of_birth": "1991-02-03",
    }
    registered = await async_client.post("/api/v1/auth/register", json=registration)
    assert registered.status_code == 201
    assert registered.json() == {"message": "User registered successfully", "phone": registration["phone"]}

    login = await async_client.post(
        "/api/v1/auth/login",
        data={"username": registration["email"], "password": registration["password"]},
    )
    assert login.status_code == 200
    credentials = login.json()
    assert credentials["token_type"] == "bearer"
    assert credentials["access_token"]
    headers = {"Authorization": f"Bearer {credentials['access_token']}"}

    booked = await async_client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "doctor_id": hospital_actors["doctor_profile"].id,
            "department_id": hospital_actors["department"].id,
            "scheduled_time": "2035-06-15T09:00:00",
            "symptoms": "persistent cough",
        },
    )
    assert booked.status_code == 201
    appointment = booked.json()
    assert appointment["id"] > 0
    assert appointment["doctor_name"] == "Doctor Journey"
    assert appointment["department_name"] == "Journey Department"
    assert appointment["status"] == "scheduled"

    queue = await async_client.get("/api/v1/appointments/queue", headers=headers)
    assert queue.status_code == 200
    assert queue.json() == {"total_waiting": 0, "average_wait_minutes": 0, "queue": []}

    cancelled = await async_client.delete(f"/api/v1/appointments/{appointment['id']}", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json() == {"message": f"Appointment {appointment['id']} canceled successfully"}


@pytest.mark.asyncio
async def test_patient_otp_round_trip_uses_configured_test_redis(async_client, monkeypatch, flush_test_redis_before_integration_test):
    redis_url = os.getenv("NAVIORA_TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("External blocker: configure NAVIORA_TEST_REDIS_URL to run the real-Redis OTP integration flow.")

    settings.REDIS_URL = redis_url
    sms = AsyncMock(return_value=True)
    monkeypatch.setattr(otp_module.sms_service, "send_otp", sms)
    phone = "+919800009102"

    generated = await async_client.post("/api/v1/auth/otp/generate", params={"phone": phone})
    assert generated.status_code == 200
    assert generated.json() == {"message": "OTP sent successfully", "phone": phone, "expires_in_seconds": 300}
    otp = sms.await_args.args[1]
    verified = await async_client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": otp})
    assert verified.status_code == 200
    assert verified.json() == {"message": "OTP verified successfully"}
