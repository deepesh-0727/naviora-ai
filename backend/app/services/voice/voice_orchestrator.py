import logging
from typing import Dict, Any
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.voice.stt_service import stt_service
from app.services.voice.tts_service import tts_service
from app.agents.hospital_brain import HospitalBrain
from app.services.intent_executor import intent_executor
from app.models.user import User
from app.models.voice_interaction import VoiceInteraction
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

class VoiceOrchestrator:
    def __init__(self):
        self.brain = HospitalBrain()
        self.session_factory = SessionLocal

    async def process_audio_command(
        self,
        db: AsyncSession,
        user: User,
        audio_data: bytes,
        session_context: Dict[str, Any],
        background_tasks: BackgroundTasks | None = None,
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

        result = {
            "query": text_query,
            "intent": analysis.get("intent"),
            "response_text": response_text,
            "audio_response": audio_response, # binary or None
            "analysis": analysis
        }
        if background_tasks is not None:
            confidence = analysis.get("confidence")
            background_tasks.add_task(
                self.persist_interaction,
                user_id=user.id,
                role=user.role,
                transcript=text_query,
                intent=analysis.get("intent"),
                confidence=float(confidence) if confidence is not None else None,
                entities=analysis.get("entities") or {},
                fallback_used=(
                    bool(analysis.get("needs_clarification"))
                    or not analysis.get("intent")
                    or (confidence is not None and float(confidence) < 0.6)
                ),
                response_text=response_text,
            )
        return result

    async def persist_interaction(
        self,
        *,
        user_id: int,
        role: str,
        transcript: str,
        intent: str | None,
        confidence: float | None,
        entities: dict[str, Any],
        fallback_used: bool,
        response_text: str,
    ) -> None:
        """Persist voice telemetry after the response is sent; logging failure is non-fatal."""
        try:
            async with self.session_factory() as db:
                db.add(
                    VoiceInteraction(
                        user_id=user_id,
                        role=role,
                        transcript=transcript,
                        intent=intent,
                        confidence=confidence,
                        entities_json=entities,
                        fallback_used=fallback_used,
                        response_text=response_text,
                    )
                )
                await db.commit()
        except Exception:
            logger.exception("Failed to persist voice interaction for user %s", user_id)

voice_orchestrator = VoiceOrchestrator()
