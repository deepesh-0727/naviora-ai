import httpx
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class STTService:
    def __init__(self, api_url: str = settings.WHISPER_API_URL):
        self.api_url = api_url

    async def transcribe(self, audio_data: bytes, language: Optional[str] = None) -> Optional[str]:
        """
        Transcribe audio bytes using the Whisper API.
        """
        files = {"file": ("audio.wav", audio_data, "audio/wav")}
        data = {"language": language} if language else {}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/transcribe",
                    files=files,
                    data=data
                )
                if response.status_code == 200:
                    result = response.json()
                    return result.get("text", "").strip()
                else:
                    logger.error(f"Whisper STT failed with status: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error calling STT service: {e}")
            return None

stt_service = STTService()
