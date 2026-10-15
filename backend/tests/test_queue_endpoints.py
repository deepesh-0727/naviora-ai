from datetime import datetime
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.doctor import Department, Doctor
from app.models.patient import Patient
from app.models.queue import QueueEntry
from app.models.user import User
from app.services import queue_service as queue_module


@pytest.fixture
async def queue_api_context(db_session, monkeypatch):
    redis_server = fakeredis.FakeServer()
    redis = fakeredis.aioredis.FakeRedis(server=redis_server, decode_responses=True)
    monkeypatch.setattr(
        queue_module.Redis,
        "from_url",
        lambda *args, **kwargs: fakeredis.aioredis.FakeRedis(server=redis_server, decode_responses=True),
    )
    monkeypatch.setattr(queue_module.ws_manager, "broadcast_event", AsyncMock(return_value=True))

    patient_user = User(phone="+919800007701", email="queue.patient@tests.example", password_hash="hash", role="patient")
    doctor_user = User(phone="+919800007702", email="queue.doctor@tests.example", password_hash="hash", role="doctor")
    orphan_doctor_user = User(phone="+919800007703", email="queue.orphan@tests.example", password_hash="hash", role="doctor")
    department = Department(name="Queue API", floor=1, building="A", wing="East", phone="100", email="queue-api@tests.example")
    db_session.add_all([patient_user, doctor_user, orphan_doctor_user, department])
    await db_session.flush()
    patient = Patient(
        user_id=patient_user.id,
        first_name="Queue",
        last_name="Patient",
        date_of_birth=datetime(1990, 1, 1),
        gender="unknown",
        emergency_contact="",
        emergency_contact_name="",
    )
    doctor = Doctor(
        user_id=doctor_user.id,
        first_name="Queue",
        last_name="Doctor",
        specialization="General",
        department_id=department.id,
        license_number="QUEUE-API-DOCTOR",
        years_of_experience=5,
        avg_consultation_time=15,
    )
    db_session.add_all([patient, doctor])
    await db_session.flush()
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        department_id=department.id,
        status="check_in",
        queue_position=1,
        scheduled_time=datetime(2030, 1, 2, 9),
    )
    db_session.add(appointment)
    await db_session.commit()
    await db_session.refresh(appointment)

    def token(user):
        return create_access_token(subject=user.id, claims={"role": user.role})

    return {
        "patient_user": patient_user,
        "patient": patient,
        "doctor_user": doctor_user,
        "orphan_doctor_user": orphan_doctor_user,
        "doctor": doctor,
        "appointment": appointment,
        "redis": redis,
        "patient_headers": {"Authorization": f"Bearer {token(patient_user)}"},
        "doctor_headers": {"Authorization": f"Bearer {token(doctor_user)}"},
        "orphan_headers": {"Authorization": f"Bearer {token(orphan_doctor_user)}"},
    }


@pytest.mark.asyncio
async def test_doctor_gets_own_queue_with_wait_estimate(async_client: AsyncClient, queue_api_context):
    ctx = queue_api_context
    await ctx["redis"].zadd(f"queue:doctor:{ctx['doctor'].id}", {str(ctx['appointment'].id): 1})

    response = await async_client.get("/api/v1/queue/status", headers=ctx["doctor_headers"])

    assert response.status_code == 200
    assert response.json()["items"] == [{
        "id": ctx["appointment"].id,
        "appointment_id": ctx["appointment"].id,
        "patient_id": ctx["patient"].id,
        "doctor_id": ctx["doctor"].id,
        "position": 1,
        "status": "check_in",
        "priority": "normal",
        "scheduled_time": "2030-01-02T09:00:00",
        "estimated_wait_minutes": 15,
    }]


@pytest.mark.asyncio
async def test_queue_status_rejects_patient_and_wrong_doctor_queue(async_client: AsyncClient, queue_api_context):
    ctx = queue_api_context
    patient_response = await async_client.get(
        f"/api/v1/queue/status?doctor_id={ctx['doctor'].id}",
        headers=ctx["patient_headers"],
    )
    wrong_doctor_response = await async_client.get(
        f"/api/v1/queue/status?doctor_id={ctx['doctor'].id + 1}",
        headers=ctx["doctor_headers"],
    )

    assert patient_response.status_code == 403
    assert patient_response.json() == {"detail": "You are not authorized to view the clinical queue."}
    assert wrong_doctor_response.status_code == 403
    assert wrong_doctor_response.json() == {"detail": "You can only view your own queue."}


@pytest.mark.asyncio
async def test_doctor_without_profile_gets_not_found(async_client: AsyncClient, queue_api_context):
    response = await async_client.get("/api/v1/queue/status", headers=queue_api_context["orphan_headers"])
    assert response.status_code == 404
    assert response.json() == {"detail": "Doctor profile not found."}


@pytest.mark.asyncio
async def test_doctor_completes_queue_item_and_persists_status(async_client: AsyncClient, queue_api_context, db_session):
    ctx = queue_api_context
    response = await async_client.put(
        f"/api/v1/queue/complete/{ctx['appointment'].id}",
        headers=ctx["doctor_headers"],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["queue_position"] == 0
    await db_session.refresh(ctx["appointment"])
    assert ctx["appointment"].status == "completed"
    repeated = await async_client.put(
        f"/api/v1/queue/complete/{ctx['appointment'].id}", headers=ctx["doctor_headers"]
    )
    assert repeated.status_code == 409
    assert repeated.json() == {"detail": "Appointment is not an active queue entry."}


@pytest.mark.asyncio
async def test_patient_cannot_complete_queue_item(async_client: AsyncClient, queue_api_context):
    ctx = queue_api_context
    response = await async_client.put(
        f"/api/v1/queue/complete/{ctx['appointment'].id}",
        headers=ctx["patient_headers"],
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "You are not authorized to complete queue appointments."}


@pytest.mark.asyncio
async def test_estimated_wait_returns_body_and_missing_doctor_is_404(async_client: AsyncClient, queue_api_context):
    ctx = queue_api_context
    response = await async_client.get(
        f"/api/v1/queue/wait-time/{ctx['doctor'].id}?position=4", headers=ctx["doctor_headers"]
    )
    missing = await async_client.get(
        f"/api/v1/queue/wait-time/{ctx['doctor'].id + 100}?position=4", headers=ctx["doctor_headers"]
    )
    assert response.status_code == 200
    assert response.json() == {"estimated_wait_minutes": 60}
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Doctor not found."}


@pytest.mark.asyncio
async def test_patient_checks_in_to_own_scheduled_appointment(async_client: AsyncClient, queue_api_context):
    ctx = queue_api_context
    ctx["appointment"].status = "scheduled"
    ctx["appointment"].queue_position = 0

    response = await async_client.post(
        f"/api/v1/queue/join/{ctx['appointment'].id}", headers=ctx["patient_headers"]
    )

    assert response.status_code == 200
    assert response.json()["id"] == ctx["appointment"].id
    assert response.json()["status"] == "check_in"
    assert response.json()["queue_position"] == 1


@pytest.mark.asyncio
async def test_patient_cannot_check_in_for_another_patient(async_client: AsyncClient, queue_api_context, db_session):
    ctx = queue_api_context
    other_user = User(phone="+919800007704", email="other.patient@tests.example", password_hash="hash", role="patient")
    db_session.add(other_user)
    await db_session.flush()
    other_patient = Patient(
        user_id=other_user.id,
        first_name="Other",
        last_name="Patient",
        date_of_birth=datetime(1990, 1, 1),
        gender="unknown",
        emergency_contact="",
        emergency_contact_name="",
    )
    db_session.add(other_patient)
    await db_session.flush()
    appointment = Appointment(
        patient_id=other_patient.id,
        doctor_id=ctx["doctor"].id,
        department_id=ctx["doctor"].department_id,
        status="scheduled",
        scheduled_time=datetime(2030, 1, 2, 9),
    )
    db_session.add(appointment)
    await db_session.commit()

    response = await async_client.post(
        f"/api/v1/queue/join/{appointment.id}", headers=ctx["patient_headers"]
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "You can only check in to your own appointment."}


@pytest.mark.asyncio
async def test_queue_join_rejects_missing_appointment(async_client: AsyncClient, queue_api_context):
    response = await async_client.post(
        "/api/v1/queue/join/999999", headers=queue_api_context["patient_headers"]
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Appointment not found or not eligible for check-in."}


@pytest.mark.asyncio
async def test_doctor_calls_next_patient_and_finishes_previous_turn(async_client: AsyncClient, queue_api_context, db_session):
    ctx = queue_api_context
    appointment = ctx["appointment"]
    db_session.add(QueueEntry(
        appointment_id=appointment.id,
        doctor_id=ctx["doctor"].id,
        position=1,
        status="queued",
        entered_at=datetime(2030, 1, 2, 9),
    ))
    await db_session.commit()

    response = await async_client.post(
        f"/api/v1/queue/next/{ctx['doctor'].id}", headers=ctx["doctor_headers"]
    )

    assert response.status_code == 200
    assert response.json()["status"] == "treating"
    assert response.json()["id"] == appointment.id
    await db_session.refresh(appointment)
    assert appointment.status == "treating"

    second_call = await async_client.post(
        f"/api/v1/queue/next/{ctx['doctor'].id}", headers=ctx["doctor_headers"]
    )
    assert second_call.status_code == 404
    assert second_call.json() == {"detail": "No patients in queue."}


@pytest.mark.asyncio
async def test_call_next_patient_enforces_doctor_role_and_ownership(async_client: AsyncClient, queue_api_context):
    ctx = queue_api_context
    patient_response = await async_client.post(
        f"/api/v1/queue/next/{ctx['doctor'].id}", headers=ctx["patient_headers"]
    )
    wrong_doctor_response = await async_client.post(
        f"/api/v1/queue/next/{ctx['doctor'].id + 1}", headers=ctx["doctor_headers"]
    )
    orphan_response = await async_client.post(
        f"/api/v1/queue/next/{ctx['doctor'].id}", headers=ctx["orphan_headers"]
    )

    assert patient_response.status_code == 403
    assert patient_response.json()["detail"].startswith("Role 'patient' is not authorized")
    assert wrong_doctor_response.status_code == 403
    assert wrong_doctor_response.json() == {"detail": "You can only call patients from your own queue."}
    assert orphan_response.status_code == 404
    assert orphan_response.json() == {"detail": "Doctor profile not found."}
