from datetime import datetime
from unittest.mock import AsyncMock

import fakeredis
import fakeredis.aioredis
import pytest
from sqlalchemy import func, select

from app.models.appointment import Appointment
from app.models.doctor import Department, Doctor
from app.models.hospital import StaffSchedule
from app.models.patient import Patient
from app.models.user import User
from app.services import availability_service
from app.services import voice_pending_service as pending_module
from app.services.voice.voice_orchestrator import VoiceOrchestrator


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2035, 6, 14, 8, 0)
        return value.replace(tzinfo=tz) if tz else value


@pytest.fixture
def fake_pending_redis(monkeypatch):
    server = fakeredis.FakeServer()
    monkeypatch.setattr(
        pending_module.Redis,
        "from_url",
        lambda *_args, **_kwargs: fakeredis.aioredis.FakeRedis(server=server, decode_responses=True),
    )


async def add_patient(db_session):
    user = User(
        phone="+919811009001",
        email="voice.confirm.patient@test.example",
        password_hash="hash",
        role="patient",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(Patient(
        user_id=user.id,
        first_name="Voice",
        last_name="Patient",
        date_of_birth=datetime(1990, 1, 1),
        gender="unknown",
        emergency_contact="",
        emergency_contact_name="",
    ))
    await db_session.flush()
    return user


async def add_bookable_doctor(db_session):
    doctor_user = User(
        phone="+919811009002",
        email="voice.confirm.doctor@test.example",
        password_hash="hash",
        role="doctor",
        is_active=True,
    )
    department = Department(
        name="Confirmation Cardiology",
        floor=1,
        building="A",
        wing="North",
        phone="101",
        email="voice.confirm.department@test.example",
    )
    db_session.add_all([doctor_user, department])
    await db_session.flush()
    doctor = Doctor(
        user_id=doctor_user.id,
        first_name="Maya",
        last_name="Confirmation",
        specialization="Cardiology",
        department_id=department.id,
        license_number="VOICE-CONFIRM-1",
        years_of_experience=8,
        is_available=True,
        max_patients_per_day=10,
        avg_consultation_time=20,
    )
    db_session.add(doctor)
    db_session.add(StaffSchedule(
        staff_id=doctor_user.id,
        date=datetime(2035, 6, 15),
        start_time=datetime(2035, 6, 15, 9),
        end_time=datetime(2035, 6, 15, 10),
        is_available=True,
    ))
    await db_session.flush()
    return doctor, department


def appointment_analysis():
    return {
        "intent": "appointment",
        "confidence": 0.9,
        "entities": {"doctor": "Maya Confirmation"},
        "specialized_details": {"preferred_time": "2035-06-15T09:00:00"},
    }


@pytest.mark.asyncio
async def test_pending_proposal_is_user_scoped_and_expires_after_120_seconds(fake_pending_redis):
    from app.services.voice_pending_service import voice_pending_service

    proposal = {"doctor_id": 12, "scheduled_time": "2035-06-15T09:00:00"}
    await voice_pending_service.set_pending(101, proposal)

    assert await voice_pending_service.get_pending(101) == proposal
    assert await voice_pending_service.get_pending(102) is None
    redis = pending_module.Redis.from_url("redis://unused", decode_responses=True)
    assert await redis.ttl(voice_pending_service.key(101)) == 120
    await redis.aclose()


@pytest.mark.asyncio
async def test_initial_booking_turn_requires_confirmation_and_creates_no_row(
    db_session, monkeypatch, fake_pending_redis
):
    monkeypatch.setattr(availability_service, "datetime", FixedDateTime)
    user = await add_patient(db_session)
    await add_bookable_doctor(db_session)
    orchestrator = VoiceOrchestrator()
    orchestrator.brain.execute = AsyncMock(return_value=appointment_analysis())

    analysis, response = await orchestrator.process_text_turn(
        db_session, user, "Book Dr. Maya Confirmation on June 15 at 9 AM", {"user_id": user.id}
    )

    assert "Confirm booking? Say yes to confirm or no to cancel." in response
    assert analysis["appointment_result"]["needs_confirmation"] is True
    assert await db_session.scalar(select(func.count(Appointment.id))) == 0


@pytest.mark.asyncio
async def test_affirmative_confirmation_creates_appointment_and_clears_pending(
    db_session, monkeypatch, fake_pending_redis
):
    monkeypatch.setattr(availability_service, "datetime", FixedDateTime)
    user = await add_patient(db_session)
    doctor, department = await add_bookable_doctor(db_session)
    orchestrator = VoiceOrchestrator()
    orchestrator.brain.execute = AsyncMock(return_value=appointment_analysis())

    await orchestrator.process_text_turn(db_session, user, "Book appointment", {"user_id": user.id})
    analysis, response = await orchestrator.process_text_turn(db_session, user, "Yes, confirm", {"user_id": user.id})

    appointment = await db_session.scalar(select(Appointment))
    assert appointment is not None
    assert appointment.patient_id == (await db_session.scalar(select(Patient.id).where(Patient.user_id == user.id)))
    assert appointment.doctor_id == doctor.id
    assert appointment.department_id == department.id
    assert "Appointment confirmed" in response
    assert analysis["appointment_result"]["confirmed"] is True
    assert await pending_module.voice_pending_service.get_pending(user.id) is None


@pytest.mark.asyncio
async def test_negative_confirmation_clears_pending_without_booking(
    db_session, monkeypatch, fake_pending_redis
):
    monkeypatch.setattr(availability_service, "datetime", FixedDateTime)
    user = await add_patient(db_session)
    await add_bookable_doctor(db_session)
    orchestrator = VoiceOrchestrator()
    orchestrator.brain.execute = AsyncMock(return_value=appointment_analysis())

    await orchestrator.process_text_turn(db_session, user, "Book appointment", {"user_id": user.id})
    analysis, response = await orchestrator.process_text_turn(db_session, user, "No, cancel it", {"user_id": user.id})

    assert "Nothing was booked" in response
    assert analysis["appointment_result"]["cancelled"] is True
    assert await pending_module.voice_pending_service.get_pending(user.id) is None
    assert await db_session.scalar(select(func.count(Appointment.id))) == 0


@pytest.mark.asyncio
async def test_new_request_clears_old_pending_before_classifying(
    db_session, monkeypatch, fake_pending_redis
):
    user = await add_patient(db_session)
    orchestrator = VoiceOrchestrator()
    orchestrator.brain.execute = AsyncMock(return_value={
        "intent": "information", "confidence": 0.9, "entities": {}, "specialized_details": {},
    })
    monkeypatch.setattr(
        "app.services.voice.voice_orchestrator.intent_executor.execute",
        AsyncMock(return_value="The hospital is open today."),
    )
    await pending_module.voice_pending_service.set_pending(user.id, {"doctor_id": 999})

    _analysis, response = await orchestrator.process_text_turn(
        db_session, user, "Where is the pharmacy?", {"user_id": user.id}
    )

    assert response == "The hospital is open today."
    orchestrator.brain.execute.assert_awaited_once()
    assert await pending_module.voice_pending_service.get_pending(user.id) is None
