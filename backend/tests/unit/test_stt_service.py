import pytest

from app.services.voice import stt_service as stt_module
from app.services.voice.stt_service import STTService


@pytest.mark.asyncio
async def test_transcribe_preserves_mobile_audio_format(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"text": "book an appointment"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, files, data):
            captured.update({"url": url, "files": files, "data": data})
            return FakeResponse()

    monkeypatch.setattr(stt_module.httpx, "AsyncClient", lambda **_kwargs: FakeClient())
    service = STTService("http://whisper.test")

    transcript = await service.transcribe(b"m4a bytes", content_type="audio/m4a")

    assert transcript == "book an appointment"
    assert captured["files"]["file"] == ("audio.m4a", b"m4a bytes", "audio/m4a")
