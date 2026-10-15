import httpx
import logging
import mimetypes
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class STTService:
    def __init__(self, api_url: str = settings.WHISPER_API_URL):
        self.api_url = api_url

    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        content_type: str = "audio/wav",
    ) -> Optional[str]:
        """
        Transcribe audio bytes using the Whisper API.
        """
        normalized_type = (content_type or "audio/wav").split(";", maxsplit=1)[0].strip().lower()
        extension = {
            "audio/m4a": ".m4a",
            "audio/mp4": ".m4a",
            "audio/3gpp": ".3gp",
            "audio/webm": ".webm",
            "audio/ogg": ".ogg",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
        }.get(normalized_type, mimetypes.guess_extension(normalized_type) or ".wav")
        files = {"file": (f"audio{extension}", audio_data, normalized_type)}
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
