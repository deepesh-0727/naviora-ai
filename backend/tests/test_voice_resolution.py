from datetime import date, datetime
from unittest.mock import AsyncMock

import fakeredis
import fakeredis.aioredis
import pytest

from app.models.doctor import Department, Doctor
from app.models.hospital import StaffSchedule
from app.models.patient import Patient
from app.models.user import User
from app.services import availability_service
from app.services import voice_pending_service as pending_module
from app.services.intent_executor import IntentExecutor
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


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("today at 2 PM", datetime(2035, 6, 14, 14)),
        ("tomorrow at 2 PM", datetime(2035, 6, 15, 14)),
        ("day after tomorrow at 14:00", datetime(2035, 6, 16, 14)),
        ("Monday at 2:30 PM", datetime(2035, 6, 18, 14, 30)),
        ("June 15 at noon", datetime(2035, 6, 15, 12)),
        ("15th at midnight", datetime(2035, 6, 15, 0)),
        ("June 15", datetime(2035, 6, 15, 14)),
        ("15th", datetime(2035, 6, 15, 14)),
        ("tomorrow", datetime(2035, 6, 15, 14)),
        ("14:00", datetime(2035, 6, 15, 14)),
    ],
)
def test_spoken_date_and_time_phrases_parse(phrase, expected):
    if phrase == "14:00":
        partial = {"date": "tomorrow", "time": phrase}
    elif phrase in {"June 15", "15th", "tomorrow"}:
        partial = {"date": phrase, "time": "2 PM"}
    else:
        partial = {"preferred_time": phrase}
    assert IntentExecutor._requested_slot(partial, today=date(2035, 6, 14)) == expected


@pytest.mark.parametrize("phrase", ["sometime soon", "June 31 at 2 PM", "after lunch"])
def test_ambiguous_or_invalid_time_is_not_guessed(phrase):
    assert IntentExecutor._requested_slot(
        {"preferred_time": phrase}, today=date(2035, 6, 14)
    ) is None


async def add_booking_data(db_session):
    user = User(
        phone="+919811009101",
        email="voice.resolution.patient@test.example",
        password_hash="hash",
        role="patient",
        is_active=True,
    )
    doctor_user = User(
        phone="+919811009102",
        email="voice.resolution.doctor@test.example",
        password_hash="hash",
        role="doctor",
        is_active=True,
    )
    department = Department(
        name="Resolution Cardiology",
        floor=1,
        building="A",
        wing="North",
        phone="101",
        email="voice.resolution.department@test.example",
    )
    db_session.add_all([user, doctor_user, department])
    await db_session.flush()
    db_session.add_all([
        Patient(
            user_id=user.id,
            first_name="Voice",
            last_name="Patient",
            date_of_birth=datetime(1990, 1, 1),
            gender="unknown",
            emergency_contact="",
            emergency_contact_name="",
        ),
        Doctor(
            user_id=doctor_user.id,
            first_name="Maya",
            last_name="Sharma",
            specialization="Cardiology",
            department_id=department.id,
            license_number="VOICE-RESOLUTION-1",
            years_of_experience=8,
            is_available=True,
            max_patients_per_day=10,
            avg_consultation_time=20,
        ),
        StaffSchedule(
            staff_id=doctor_user.id,
            date=datetime(2035, 6, 15),
            start_time=datetime(2035, 6, 15, 9),
            end_time=datetime(2035, 6, 15, 10),
            is_available=True,
        ),
    ])
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_fuzzy_doctor_name_resolves_unique_close_match(db_session, monkeypatch):
    from app.services import intent_executor as executor_module

    monkeypatch.setattr(availability_service, "datetime", FixedDateTime)
    monkeypatch.setattr(executor_module, "datetime", FixedDateTime)
    user = await add_booking_data(db_session)
    result = await executor_module.IntentExecutor().execute(db_session, user, {
        "intent": "appointment",
        "confidence": 0.9,
        "entities": {"doctor": "Maya Sharm"},
        "specialized_details": {"preferred_time": "tomorrow at 9 AM"},
    })
    assert result["needs_confirmation"] is True
    assert result["booking_proposal"]["doctor_name"] == "Dr. Maya Sharma"


@pytest.mark.asyncio
async def test_followup_time_resumes_clarification_and_requests_confirmation(
    db_session, monkeypatch, fake_pending_redis
):
    monkeypatch.setattr(availability_service, "datetime", FixedDateTime)
    from app.services import intent_executor as executor_module
    monkeypatch.setattr(executor_module, "datetime", FixedDateTime)
    user = await add_booking_data(db_session)
    orchestrator = VoiceOrchestrator()
    orchestrator.brain.execute = AsyncMock(return_value={
        "intent": "appointment",
        "confidence": 0.9,
        "entities": {"doctor": "Maya Sharma"},
        "specialized_details": {},
    })

    _analysis, first_response = await orchestrator.process_text_turn(
        db_session, user, "Book with Dr Maya Sharma", {"user_id": user.id}
    )
    analysis, followup_response = await orchestrator.process_text_turn(
        db_session, user, "tomorrow at 9 AM", {"user_id": user.id}
    )

    assert "When would you like" in first_response
    assert "Confirm booking? Say yes" in followup_response
    assert analysis["appointment_result"]["needs_confirmation"] is True


@pytest.mark.asyncio
async def test_second_failed_time_parse_escalates_to_reception(
    db_session, monkeypatch, fake_pending_redis
):
    monkeypatch.setattr(availability_service, "datetime", FixedDateTime)
    from app.services import intent_executor as executor_module
    monkeypatch.setattr(executor_module, "datetime", FixedDateTime)
    user = await add_booking_data(db_session)
    orchestrator = VoiceOrchestrator()
    orchestrator.brain.execute = AsyncMock(return_value={
        "intent": "appointment",
        "confidence": 0.9,
        "entities": {"doctor": "Maya Sharma"},
        "specialized_details": {"preferred_time": "sometime soon"},
    })

    _analysis, _first_response = await orchestrator.process_text_turn(
        db_session, user, "Book with Dr Maya Sharma sometime soon", {"user_id": user.id}
    )
    analysis, response = await orchestrator.process_text_turn(
        db_session, user, "after lunch", {"user_id": user.id}
    )

    assert response == "Let me connect you to reception."
    assert analysis["appointment_result"]["time_parse_failures"] == 2
    assert await pending_module.voice_pending_service.get_resolution(user.id) is None
