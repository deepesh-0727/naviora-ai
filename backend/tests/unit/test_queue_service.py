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
from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError


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
    return db_session, appointment, doctor, patient, redis


@pytest.mark.asyncio
async def test_queue_add_active_appointment_sets_position_and_eta(active_appointment):
    db, appointment, doctor, _, redis = active_appointment

    result = await QueueService().add_to_queue(db, appointment.id, doctor.id)

    assert result == {"position": 1, "estimated_wait_minutes": 20}
    entry = await db.get(QueueEntry, appointment.id)
    assert entry is not None
    assert entry.status == "queued"
    assert await redis.zrank(QueueService._queue_key(doctor.id), str(appointment.id)) == 0


@pytest.mark.asyncio
async def test_queue_wait_time_uses_persisted_doctor_average(active_appointment):
    db, _, doctor, _, _ = active_appointment

    assert await QueueService().calculate_wait_time(db, doctor.id, 3) == 60


@pytest.mark.asyncio
async def test_queue_add_inactive_appointment_is_rejected(active_appointment):
    db, appointment, doctor, _, _ = active_appointment
    appointment.status = "cancelled"
    await db.commit()

    with pytest.raises(Exception) as error:
        await QueueService().add_to_queue(db, appointment.id, doctor.id)

    assert getattr(error.value, "status_code", None) == 404


async def _new_appointment(db, patient, doctor, *, status="check_in", scheduled_time=None):
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        department_id=doctor.department_id,
        status=status,
        scheduled_time=scheduled_time or datetime(2030, 1, 2, 10, 0),
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return appointment


@pytest.mark.asyncio
async def test_queue_add_is_idempotent_and_positions_follow_redis_score(active_appointment):
    db, first, doctor, patient, redis = active_appointment
    second = await _new_appointment(db, patient, doctor, scheduled_time=datetime(2030, 1, 2, 10, 30))
    service = QueueService()

    first_result = await service.add_to_queue(db, first.id, doctor.id)
    second_result = await service.add_to_queue(db, second.id, doctor.id)
    duplicate_result = await service.add_to_queue(db, first.id, doctor.id)

    assert first_result == {"position": 1, "estimated_wait_minutes": 20}
    assert second_result == {"position": 2, "estimated_wait_minutes": 40}
    assert duplicate_result == first_result
    assert await redis.zcard(service._queue_key(doctor.id)) == 2
    assert (await db.get(Appointment, second.id)).queue_position == 2
    assert queue_module.ws_manager.broadcast_event.await_count >= 3


@pytest.mark.asyncio
async def test_get_queue_status_rehydrates_order_and_removes_stale_members(active_appointment):
    db, first, doctor, patient, redis = active_appointment
    second = await _new_appointment(db, patient, doctor, scheduled_time=datetime(2030, 1, 2, 9, 30))
    db.add_all([
        QueueEntry(appointment_id=first.id, doctor_id=doctor.id, position=8, entered_at=datetime(2030, 1, 2, 9, 0)),
        QueueEntry(appointment_id=second.id, doctor_id=doctor.id, position=9, entered_at=datetime(2030, 1, 2, 9, 30)),
    ])
    await db.commit()
    items = await QueueService().get_queue_status(db, doctor.id)

    assert [item["appointment_id"] for item in items] == [first.id, second.id]
    assert [item["position"] for item in items] == [1, 2]
    assert [item["estimated_wait_minutes"] for item in items] == [20, 40]
    await redis.zadd(QueueService._queue_key(doctor.id), {"999999": 1})
    items_with_stale_member = await QueueService().get_queue_status(db, doctor.id)
    assert [item["appointment_id"] for item in items_with_stale_member] == [first.id, second.id]
    assert await redis.zscore(QueueService._queue_key(doctor.id), "999999") is None
    assert (await db.get(QueueEntry, first.id)).position == 1


@pytest.mark.asyncio
async def test_get_queue_status_returns_empty_when_no_members(active_appointment):
    db, _, doctor, _, _ = active_appointment

    assert await QueueService().get_queue_status(db, doctor.id) == []


@pytest.mark.asyncio
async def test_calculate_wait_time_rejects_missing_doctor_and_clamps_negative_position(active_appointment):
    db, _, doctor, _, _ = active_appointment
    assert await QueueService().calculate_wait_time(db, doctor.id, -3) == 0
    with pytest.raises(HTTPException) as error:
        await QueueService().calculate_wait_time(db, doctor.id + 999, 1)
    assert error.value.status_code == 404
    assert error.value.detail == "Doctor not found."


@pytest.mark.asyncio
async def test_mark_served_updates_appointment_entry_and_removes_redis_member(active_appointment):
    db, appointment, doctor, _, redis = active_appointment
    await QueueService().add_to_queue(db, appointment.id, doctor.id)
    entry = await db.get(QueueEntry, appointment.id)

    served = await QueueService().mark_served(db, appointment.id, doctor.id)

    await db.refresh(appointment)
    await db.refresh(entry)
    assert served is True
    assert appointment.status == "completed"
    assert appointment.queue_position == 0
    assert entry.status == "served"
    assert entry.position == 0
    assert entry.served_at is not None
    assert await redis.zscore(QueueService._queue_key(doctor.id), str(appointment.id)) is None
    assert await QueueService().mark_served(db, appointment.id, doctor.id) is False


@pytest.mark.asyncio
async def test_join_queue_checks_in_scheduled_appointment(active_appointment):
    db, appointment, doctor, _, redis = active_appointment
    appointment.status = "scheduled"
    await db.commit()

    joined = await QueueService().join_queue(db, appointment.id)

    assert joined.id == appointment.id
    assert joined.status == "check_in"
    assert joined.actual_time is not None
    assert joined.queue_position == 1
    assert await redis.zrank(QueueService._queue_key(doctor.id), str(appointment.id)) == 0
    assert await QueueService().join_queue(db, appointment.id) is None
    assert await QueueService().join_queue(db, appointment.id + 999) is None


@pytest.mark.asyncio
async def test_get_next_patient_advances_and_broadcasts_turn(active_appointment):
    db, appointment, doctor, patient, redis = active_appointment
    await QueueService().add_to_queue(db, appointment.id, doctor.id)

    next_patient = await QueueService().get_next_patient(db, doctor.id)

    await db.refresh(appointment)
    entry = await db.get(QueueEntry, appointment.id)
    assert next_patient.id == appointment.id
    assert appointment.status == "treating"
    assert entry.status == "treating"
    queue_module.ws_manager.broadcast_event.assert_any_await(
        f"patient:{patient.id}",
        "queue_alert",
        {"message": "It is your turn. Please proceed to the doctor's cabin."},
    )
    assert await QueueService().get_next_patient(db, doctor.id) is None
    assert await redis.zscore(QueueService._queue_key(doctor.id), str(appointment.id)) is None


@pytest.mark.asyncio
async def test_redis_failure_is_reported_and_rolls_back_membership(active_appointment, monkeypatch):
    db, appointment, doctor, _, redis = active_appointment
    appointment_id = appointment.id
    doctor_id = doctor.id
    original_zadd = redis.zadd

    async def failing_zadd(*args, **kwargs):
        raise RedisConnectionError("test redis unavailable")

    monkeypatch.setattr(redis, "zadd", failing_zadd)
    with pytest.raises(HTTPException) as error:
        await QueueService().add_to_queue(db, appointment_id, doctor_id)
    assert error.value.status_code == 503
    assert error.value.detail == "Queue service is unavailable."
    await db.refresh(appointment)
    assert appointment.queue_position == 0
    monkeypatch.setattr(redis, "zadd", original_zadd)
