import base64
import io
import wave
from unittest.mock import AsyncMock

import pytest


def deterministic_wav() -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 160)
    return stream.getvalue()


@pytest.mark.asyncio
async def test_voice_journey_transcribes_triages_and_returns_spoken_response(async_client, hospital_actors, monkeypatch):
    from app.services.voice import stt_service, tts_service
    from app.services.voice.voice_orchestrator import voice_orchestrator
    from app.services.emergency_service import emergency_service

    monkeypatch.setattr(
        stt_service.stt_service,
        "transcribe",
        AsyncMock(return_value="chest pain at the main lobby"),
    )
    monkeypatch.setattr(
        voice_orchestrator.brain,
        "execute",
        AsyncMock(return_value={
            "intent": "emergency",
            "confidence": 0.99,
            "entities": {},
            "specialized_details": {
                "emergency_type": "chest pain",
                "severity": 2,
                "location_clues": "main lobby",
                "immediate_action_required": "wait for help",
            },
        }),
    )
    monkeypatch.setattr(
        emergency_service.agent,
        "execute",
        AsyncMock(return_value={
            "emergency_type": "chest pain",
            "severity": 2,
            "location_clues": "main lobby",
            "immediate_action_required": "wait for help",
        }),
    )
    monkeypatch.setattr(
        tts_service.tts_service,
        "synthesize",
        AsyncMock(return_value=b"deterministic-audio"),
    )
    headers = {"Authorization": f"Bearer {hospital_actors['tokens']['patient']}"}
    response = await async_client.post(
        "/api/v1/voice/process",
        headers=headers,
        files={"audio": ("fixture.wav", deterministic_wav(), "audio/wav")},
        data={"session_id": "voice-journey-1", "return_audio": "true"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "chest pain at the main lobby"
    assert body["intent"] == "emergency"
    assert body["response_text"].startswith("Emergency request ")
    assert base64.b64decode(body["audio_response_b64"]) == b"deterministic-audio"
    assert body["session_id"] == "voice-journey-1"
