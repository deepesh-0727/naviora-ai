import pytest
from datetime import datetime
from httpx import AsyncClient

from app.agents.base_agent import BaseAgent
from app.core.config import settings
from app.core.security import create_access_token
from app.models.doctor import Department, Doctor
from app.models.hospital import StaffSchedule
from app.models.patient import Patient
from app.models.user import User
from app.services import availability_service
from app.services import voice_pending_service as pending_module
from app.services.voice import stt_service, tts_service
from app.services import cache_service


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2035, 6, 14, 8, 0)
        return value.replace(tzinfo=tz) if tz else value


@pytest.mark.asyncio
async def test_voice_processing_requires_authentication(async_client: AsyncClient):
    response = await async_client.post("/api/v1/voice/process")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_voice_uses_rule_fallback_and_still_requests_booking_confirmation(
    async_client: AsyncClient, db_session, monkeypatch
):
    import fakeredis
    import fakeredis.aioredis
    import httpx
    from app.services import intent_executor as executor_module

    redis_server = fakeredis.FakeServer()
    monkeypatch.setattr(
        pending_module.Redis,
        "from_url",
        lambda *_args, **_kwargs: fakeredis.aioredis.FakeRedis(
            server=redis_server, decode_responses=True
        ),
    )
    monkeypatch.setattr(availability_service, "datetime", FixedDateTime)
    monkeypatch.setattr(executor_module, "datetime", FixedDateTime)
    monkeypatch.setattr(settings, "AI_MAX_RETRIES", 1)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")

    async def raise_connection_error(*_args, **_kwargs):
        raise httpx.ConnectError("Ollama unreachable")

    async def no_cached_intent(*_args, **_kwargs):
        return None

    async def ignore_cached_intent(*_args, **_kwargs):
        return None

    monkeypatch.setattr(BaseAgent, "_call_ollama", raise_connection_error)
    monkeypatch.setattr(cache_service.cache_service, "get_cached_intent", no_cached_intent)
    monkeypatch.setattr(cache_service.cache_service, "set_cached_intent", ignore_cached_intent)
    async def transcribe(_audio, language=None, content_type="audio/wav"):
        return "Book appointment with Dr. Sharma tomorrow at 9 AM"

    monkeypatch.setattr(stt_service.stt_service, "transcribe", transcribe)
    monkeypatch.setattr(tts_service.tts_service, "synthesize", no_cached_intent)

    patient_user = User(
        phone="+919811009201",
        email="voice.fallback.patient@test.example",
        password_hash="hash",
        role="patient",
        is_active=True,
    )
    doctor_user = User(
        phone="+919811009202",
        email="voice.fallback.doctor@test.example",
        password_hash="hash",
        role="doctor",
        is_active=True,
    )
    department = Department(
        name="Fallback Cardiology",
        floor=1,
        building="A",
        wing="North",
        phone="101",
        email="voice.fallback.department@test.example",
    )
    db_session.add_all([patient_user, doctor_user, department])
    await db_session.flush()
    db_session.add_all([
        Patient(
            user_id=patient_user.id,
            first_name="Rule",
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
            license_number="VOICE-FALLBACK-1",
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
    await db_session.commit()
    token = create_access_token(subject=patient_user.id, claims={"role": "patient"})

    response = await async_client.post(
        "/api/v1/voice/process",
        headers={"Authorization": f"Bearer {token}"},
        files={"audio": ("test.wav", b"RIFF....WAVEfmt ", "audio/wav")},
        data={"return_audio": "false"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["fallback_used"] is True
    assert body["fallback_reason"] == "llm_unreachable"
    assert body["intent"] == "appointment"
    assert body["analysis"]["appointment_result"]["needs_confirmation"] is True
    assert "Confirm booking? Say yes" in body["response_text"]
