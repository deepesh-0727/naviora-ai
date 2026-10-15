import base64
import io
import json
import wave
from unittest.mock import AsyncMock

import httpx
import pytest

from app.services import cache_service as cache_module


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

    cache_read = AsyncMock(return_value=None)
    cache_write = AsyncMock(return_value=True)
    monkeypatch.setattr(cache_module.cache_service, "get_cached_intent", cache_read)
    monkeypatch.setattr(cache_module.cache_service, "set_cached_intent", cache_write)

    response_json = json.dumps({
        "intent": "emergency",
        "confidence": 0.99,
        "entities": {},
        "emergency_type": "chest pain",
        "severity": 2,
        "location_clues": "main lobby",
        "immediate_action_required": "wait for help",
    })

    class MockVoiceHTTPClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            if url.endswith("/transcribe"):
                return httpx.Response(200, json={"text": "chest pain at the main lobby"})
            return httpx.Response(200, json={"response": response_json})

        async def get(self, url, **kwargs):
            assert url.endswith("/say")
            return httpx.Response(200, content=b"deterministic-audio")

    monkeypatch.setattr(stt_service.httpx, "AsyncClient", MockVoiceHTTPClient)
    monkeypatch.setattr(tts_service.httpx, "AsyncClient", MockVoiceHTTPClient)
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
