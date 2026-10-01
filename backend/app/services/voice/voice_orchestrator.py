import logging
import io
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.voice.stt_service import stt_service
from app.services.voice.tts_service import tts_service
from app.agents.hospital_brain import HospitalBrain
from app.services.intent_executor import intent_executor
from app.models.user import User

logger = logging.getLogger(__name__)

class VoiceOrchestrator:
    def __init__(self):
        self.brain = HospitalBrain()

    async def process_audio_command(
        self,
        db: AsyncSession,
        user: User,
        audio_data: bytes,
        session_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        The full Voice-to-Action loop.
        1. Audio -> Text (STT)
        2. Text -> Intent (Brain)
        3. Intent -> Action (Executor)
        4. Response Text -> Audio (TTS)
        """
        # 1. Speech to Text
        text_query = await stt_service.transcribe(audio_data)
        if not text_query:
            return {"error": "Could not transcribe audio"}

        # 2. Intent Classification & Entity Extraction
        analysis = await self.brain.execute(text_query, session_context)

        # 3. Execute Action & Get Text Response
        response_text = await intent_executor.execute(db, user, analysis)

        # 4. Text to Speech
        audio_response = await tts_service.synthesize(response_text)

        return {
            "query": text_query,
            "intent": analysis.get("intent"),
            "response_text": response_text,
            "audio_response": audio_response, # binary or None
            "analysis": analysis
        }

voice_orchestrator = VoiceOrchestrator()
