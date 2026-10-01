import httpx
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self, api_url: str = settings.PIPER_API_URL):
        self.api_url = api_url
        self._cache = {}

    async def synthesize(self, text: str, voice: str = "en_US-lessac-medium") -> Optional[bytes]:
        """
        Synthesize text to speech using the Piper API.
        """
        # Simple caching for performance
        cache_key = f"{text}_{voice}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_url}/say",
                    params={"text": text, "voice": voice}
                )
                if response.status_code == 200:
                    audio_content = response.content
                    # Cache short common responses (under 100 chars)
                    if len(text) < 100:
                        self._cache[cache_key] = audio_content
                    return audio_content
                else:
                    logger.error(f"Piper TTS failed with status: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error calling TTS service: {e}")
            return None

tts_service = TTSService()
