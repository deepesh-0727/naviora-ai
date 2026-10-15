from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.models.appointment import Appointment
from app.models.doctor import Department, Doctor
from app.models.patient import Patient
from app.models.queue import QueueEntry
from app.models.user import User
from app.services import queue_service as queue_module
from app.services.queue_service import QueueService


@pytest.fixture
async def active_appointment(db_session, monkeypatch):
    user = User(phone="+919800000201", email="doctor.queue@tests.example", password_hash="hash", role="doctor")
    patient_user = User(phone="+919800000202", email="patient.queue@tests.example", password_hash="hash", role="patient")
    department = Department(name="Queue Tests", floor=1, building="A", wing="East", phone="100", email="queue@tests.example")
    db_session.add_all([user, patient_user, department])
    await db_session.flush()
    patient = Patient(user_id=patient_user.id, first_name="Test", last_name="Patient", date_of_birth=datetime(1990, 1, 1), gender="unknown", emergency_contact="", emergency_contact_name="")
    doctor = Doctor(user_id=user.id, first_name="Test", last_name="Doctor", specialization="General", department_id=department.id, license_number="QUEUE-TEST-1", years_of_experience=5, avg_consultation_time=20)
    db_session.add_all([patient, doctor])
    await db_session.flush()
    appointment = Appointment(patient_id=patient.id, doctor_id=doctor.id, department_id=department.id, status="check_in", scheduled_time=datetime(2030, 1, 2, 9, 0))
    db_session.add(appointment)
    await db_session.commit()
    await db_session.refresh(appointment)
    fakeredis = pytest.importorskip("fakeredis.aioredis", reason="fakeredis[lua] dev dependency is unavailable")
    redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(queue_module.Redis, "from_url", lambda *args, **kwargs: redis)
    monkeypatch.setattr(queue_module.ws_manager, "broadcast_event", AsyncMock())
    monkeypatch.setattr(QueueService, "notify_queue_updates", AsyncMock())
    return db_session, appointment, doctor, redis


@pytest.mark.asyncio
async def test_queue_add_active_appointment_sets_position_and_eta(active_appointment):
    db, appointment, doctor, redis = active_appointment

    result = await QueueService().add_to_queue(db, appointment.id, doctor.id)

    assert result == {"position": 1, "estimated_wait_minutes": 20}
    entry = await db.get(QueueEntry, appointment.id)
    assert entry is not None
    assert entry.status == "queued"
    assert await redis.zrank(QueueService._queue_key(doctor.id), str(appointment.id)) == 0


@pytest.mark.asyncio
async def test_queue_wait_time_uses_persisted_doctor_average(active_appointment):
    db, _, doctor, _ = active_appointment

    assert await QueueService().calculate_wait_time(db, doctor.id, 3) == 60


@pytest.mark.asyncio
async def test_queue_add_inactive_appointment_is_rejected(active_appointment):
    db, appointment, doctor, _ = active_appointment
    appointment.status = "cancelled"
    await db.commit()

    with pytest.raises(Exception) as error:
        await QueueService().add_to_queue(db, appointment.id, doctor.id)

    assert getattr(error.value, "status_code", None) == 404
