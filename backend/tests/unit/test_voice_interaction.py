from unittest.mock import AsyncMock

import pytest

from app.core.security import create_access_token
from app.models.user import User
from app.models.voice_interaction import VoiceInteraction
from app.services.voice import stt_service, tts_service
from app.services.voice.voice_orchestrator import intent_executor, voice_orchestrator
from sqlalchemy import select


@pytest.mark.asyncio
async def test_voice_process_persists_interaction_after_response(
    async_client, db_session, monkeypatch, test_session_factory
):
    user = User(
        phone="+919811002101",
        email="voice.staff@test.example",
        password_hash="hash",
        role="staff",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    token = create_access_token(subject=user.id, claims={"role": "staff"})

    monkeypatch.setattr(stt_service.stt_service, "transcribe", AsyncMock(return_value="Book cardiology"))
    monkeypatch.setattr(
        voice_orchestrator.brain,
        "execute",
        AsyncMock(return_value={
            "intent": "appointment",
            "confidence": 0.91,
            "entities": {"department": "cardiology"},
            "specialized_details": {},
        }),
    )
    monkeypatch.setattr(intent_executor, "execute", AsyncMock(return_value="Appointment request recorded."))
    monkeypatch.setattr(tts_service.tts_service, "synthesize", AsyncMock(return_value=None))
    monkeypatch.setattr(voice_orchestrator, "session_factory", test_session_factory)

    response = await async_client.post(
        "/api/v1/voice/process",
        headers={"Authorization": f"Bearer {token}"},
        data={"return_audio": "false"},
        files={"audio": ("request.wav", b"fake wav payload", "audio/wav")},
    )

    assert response.status_code == 200, response.text
    assert response.json()["intent"] == "appointment"
    interaction = await db_session.scalar(
        select(VoiceInteraction).where(VoiceInteraction.user_id == user.id)
    )
    assert interaction is not None
    assert interaction.role == "staff"
    assert interaction.transcript == "Book cardiology"
    assert interaction.intent == "appointment"
    assert interaction.confidence == 0.91
    assert interaction.entities_json == {"department": "cardiology"}
    assert interaction.fallback_used is False
    assert interaction.response_text == "Appointment request recorded."


@pytest.mark.asyncio
async def test_voice_process_returns_retry_message_when_audio_cannot_be_transcribed(
    async_client, db_session, monkeypatch
):
    user = User(
        phone="+919811002102",
        email="voice.transcription.failure@test.example",
        password_hash="hash",
        role="patient",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    token = create_access_token(subject=user.id, claims={"role": "patient"})
    monkeypatch.setattr(stt_service.stt_service, "transcribe", AsyncMock(return_value=None))

    response = await async_client.post(
        "/api/v1/voice/process",
        headers={"Authorization": f"Bearer {token}"},
        data={"return_audio": "false"},
        files={"audio": ("request.m4a", b"unrecognized audio", "audio/mp4")},
    )

    assert response.status_code == 200
    assert response.json()["text"] == ""
    assert response.json()["response_text"] == "I couldn't hear that. Please try again."
    assert response.json()["fallback_used"] is True
