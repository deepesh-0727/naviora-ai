import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.voice.stt_service import stt_service
from app.services.voice.tts_service import tts_service
from app.agents.hospital_brain import HospitalBrain
from app.services.intent_executor import IntentExecutor, intent_executor
from app.models.user import User
from app.models.appointment import Appointment
from app.models.doctor import Department, Doctor
from app.models.patient import Patient
from app.models.voice_interaction import VoiceInteraction
from app.db.session import SessionLocal
from app.services.availability_service import database_datetime, get_available_slots
from app.services.voice_pending_service import voice_pending_service
from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)

class VoiceOrchestrator:
    _NEW_REQUEST_WORDS = (
        "appointment", "book", "schedule", "reschedule", "emergency", "sos",
        "directions", "where is", "pharmacy", "prescription", "visiting hours", "cancel",
        "hospital hours", "billing", "invoice",
    )

    def __init__(self):
        self.brain = HospitalBrain()
        self.session_factory = SessionLocal

    @staticmethod
    def _confirmation_decision(text: str) -> str | None:
        normalized = text.casefold().replace("’", "'")
        normalized = re.sub(r"[^a-z\s']", " ", normalized)
        normalized = " ".join(normalized.split())
        affirmative = {
            "yes", "yeah", "yep", "sure", "confirm", "confirm booking",
            "yes please", "yes confirm", "yes confirm booking", "yes book it",
            "please confirm", "book it", "go ahead", "proceed",
        }
        negative = {
            "no", "nope", "no cancel", "no cancel it", "cancel", "cancel it", "cancel booking", "stop",
            "never mind", "nevermind", "no thank you", "no thanks", "don't book",
        }
        if normalized in affirmative:
            return "confirm"
        if normalized in negative:
            return "cancel"
        return None

    @classmethod
    def _is_new_request(cls, text: str) -> bool:
        normalized = text.casefold()
        return any(word in normalized for word in cls._NEW_REQUEST_WORDS)

    async def process_text_turn(
        self,
        db: AsyncSession,
        user: User,
        text: str,
        session_context: Dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        """Process a transcript, including a user-scoped pending confirmation."""
        pending = await voice_pending_service.get_pending(user.id)
        decision = self._confirmation_decision(text) if pending else None
        if pending and decision == "confirm":
            proposal = await voice_pending_service.pop_pending(user.id)
            if proposal is None:
                response = "That booking request expired. Please tell me the appointment details again."
                return {"intent": "appointment", "confidence": 1.0, "entities": {}}, response
            response = await self._confirm_appointment(db, user, proposal)
            return {
                "intent": "appointment",
                "confidence": 1.0,
                "entities": {},
                "appointment_result": {"needs_confirmation": False, "confirmed": "Appointment " in response},
            }, response
        if pending and decision == "cancel":
            await voice_pending_service.clear_pending(user.id)
            response = "The appointment request is cancelled. Nothing was booked."
            return {
                "intent": "appointment",
                "confidence": 1.0,
                "entities": {},
                "appointment_result": {"needs_confirmation": False, "cancelled": True},
            }, response
        if pending:
            # A non-confirmation utterance is a new request; do not retain stale intent.
            await voice_pending_service.clear_pending(user.id)
            await voice_pending_service.clear_resolution(user.id)

        resolution = await voice_pending_service.get_resolution(user.id)
        if resolution and self._confirmation_decision(text) == "cancel":
            await voice_pending_service.clear_resolution(user.id)
            return {
                "intent": "appointment", "confidence": 1.0, "entities": {},
                "appointment_result": {"needs_clarification": False, "cancelled": True},
            }, "The appointment request is cancelled. Nothing was booked."
        if resolution and not self._is_new_request(text):
            prior = resolution.get("partial_intent") or {}
            partial = dict(prior) if isinstance(prior, dict) else {}
            doctor_name = partial.get("doctor_name")
            candidates = resolution.get("candidates") or []
            if not doctor_name:
                partial["doctor_name"] = text.strip()
            elif candidates and any(
                text.casefold() in str(candidate).casefold() for candidate in candidates
            ):
                chosen = next(
                    (str(candidate) for candidate in candidates if text.casefold() in str(candidate).casefold()),
                    text,
                )
                doctor_label, _, department = chosen.partition(" — ")
                partial["doctor_name"] = doctor_label
                if department:
                    partial["department_name"] = department
            else:
                partial["preferred_time"] = text.strip()

            resumed_analysis = {
                "intent": "appointment",
                "confidence": 0.9,
                "entities": {
                    "doctor": partial.get("doctor_name"),
                    "department": partial.get("department_name"),
                    "date": partial.get("date"),
                    "time": partial.get("time"),
                    "symptoms": partial.get("symptoms"),
                },
                "specialized_details": {"preferred_time": partial.get("preferred_time")},
            }
            execution_result = await intent_executor.execute(db, user, resumed_analysis)
            if isinstance(execution_result, dict):
                if execution_result.get("needs_confirmation") and execution_result.get("booking_proposal"):
                    await voice_pending_service.clear_resolution(user.id)
                    await voice_pending_service.set_pending(user.id, execution_result["booking_proposal"])
                    execution_result = {
                        **execution_result,
                        "response_text": (
                            f"{execution_result.get('response_text', '').strip()} "
                            "Confirm booking? Say yes to confirm or no to cancel."
                        ).strip(),
                    }
                elif execution_result.get("needs_clarification"):
                    failures = int(resolution.get("failed_time_parses", 0))
                    attempted_time = bool(
                        partial.get("preferred_time") or partial.get("date") or partial.get("time")
                    )
                    if (
                        partial.get("doctor_name")
                        and attempted_time
                        and IntentExecutor._requested_slot(partial) is None
                    ):
                        failures += 1
                        if failures >= 2:
                            await voice_pending_service.clear_resolution(user.id)
                            return {
                                "intent": "appointment", "confidence": 0.9, "entities": {},
                                "appointment_result": {"needs_clarification": True, "time_parse_failures": failures},
                            }, "Let me connect you to reception."
                    await voice_pending_service.set_resolution(user.id, {
                        "partial_intent": execution_result.get("partial_intent", partial),
                        "candidates": execution_result.get("candidates", []),
                        "failed_time_parses": failures,
                    })
                response_text = str(execution_result.get("response_text") or "")
                return {**resumed_analysis, "appointment_result": execution_result}, response_text

        if resolution:
            # A clearly different command supersedes the old clarification context.
            await voice_pending_service.clear_resolution(user.id)

        analysis = await self.brain.execute(text, session_context)
        execution_result = await intent_executor.execute(db, user, analysis)
        if isinstance(execution_result, dict):
            if execution_result.get("needs_confirmation") and execution_result.get("booking_proposal"):
                await voice_pending_service.clear_resolution(user.id)
                await voice_pending_service.set_pending(user.id, execution_result["booking_proposal"])
                execution_result = {
                    **execution_result,
                    "response_text": (
                        f"{execution_result.get('response_text', '').strip()} "
                        "Confirm booking? Say yes to confirm or no to cancel."
                    ).strip(),
                }
            elif analysis.get("intent") == "appointment" and execution_result.get("needs_clarification"):
                partial = execution_result.get("partial_intent") or {}
                requested_slot = IntentExecutor._requested_slot(partial)
                attempts = 1 if (
                    partial.get("doctor_name")
                    and (partial.get("date") or partial.get("time") or partial.get("preferred_time"))
                    and requested_slot is None
                ) else 0
                await voice_pending_service.set_resolution(user.id, {
                    "partial_intent": partial,
                    "candidates": execution_result.get("candidates", []),
                    "failed_time_parses": attempts,
                })
            response_text = str(execution_result.get("response_text") or "")
            analysis = {**analysis, "appointment_result": execution_result}
        else:
            response_text = execution_result
        return analysis, response_text

    async def _confirm_appointment(
        self,
        db: AsyncSession,
        user: User,
        proposal: dict[str, Any],
    ) -> str:
        """Revalidate and create the appointment only after explicit confirmation."""
        if user.role != "patient":
            return "Only a patient account can confirm an appointment. Nothing was booked."
        patient_id = await db.scalar(select(Patient.id).where(Patient.user_id == user.id))
        try:
            scheduled_time = database_datetime(datetime.fromisoformat(str(proposal.get("scheduled_time", ""))))
        except ValueError:
            return "That booking request is invalid. Please tell me the appointment details again."
        if patient_id is None or patient_id != proposal.get("patient_id"):
            return "I could not verify your patient profile. Nothing was booked."
        doctor_result = await db.execute(
            select(Doctor, Department)
            .join(Department, Department.id == Doctor.department_id)
            .join(User, User.id == Doctor.user_id)
            .where(
                Doctor.id == proposal.get("doctor_id"),
                Department.id == proposal.get("department_id"),
                Doctor.is_available.is_(True),
                User.is_active.is_(True),
            )
        )
        row = doctor_result.one_or_none()
        if row is None:
            return "That doctor is no longer available. Please request another appointment."
        doctor, department = row
        slots = [
            database_datetime(datetime.fromisoformat(slot))
            for slot in await get_available_slots(db, doctor, scheduled_time.date())
        ]
        if scheduled_time not in slots:
            return "That slot is no longer available. Please request another time."

        day_start = scheduled_time.replace(hour=0, minute=0, second=0, microsecond=0)
        count = await db.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.doctor_id == doctor.id,
                Appointment.scheduled_time >= day_start,
                Appointment.scheduled_time < day_start + timedelta(days=1),
                Appointment.status == "scheduled",
            )
        )
        position = int(count or 0) + 1
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor.id,
            department_id=department.id,
            scheduled_time=scheduled_time,
            status="scheduled",
            queue_position=position,
            wait_time_minutes=position * max(doctor.avg_consultation_time, 1),
            symptoms=proposal.get("symptoms"),
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)
        event = {
            "appointment_id": appointment.id,
            "doctor_id": doctor.id,
            "patient_id": patient_id,
            "scheduled_time": scheduled_time.isoformat(),
            "status": appointment.status,
            "queue_position": position,
        }
        await ws_manager.broadcast_event(f"doctor:{doctor.id}", "queue_update", event)
        await ws_manager.broadcast_event(f"patient:{patient_id}", "queue_update", event)
        return f"Appointment confirmed with Dr. {doctor.first_name} {doctor.last_name}. Your queue position is {position}."

    async def process_audio_command(
        self,
        db: AsyncSession,
        user: User,
        audio_data: bytes,
        session_context: Dict[str, Any],
        background_tasks: BackgroundTasks | None = None,
        audio_content_type: str = "audio/wav",
    ) -> Dict[str, Any]:
        """
        The full Voice-to-Action loop.
        1. Audio -> Text (STT)
        2. Text -> Intent (Brain)
        3. Intent -> Action (Executor)
        4. Response Text -> Audio (TTS)
        """
        # 1. Speech to Text
        text_query = await stt_service.transcribe(audio_data, content_type=audio_content_type)
        if not text_query:
            return {"error": "Could not transcribe audio"}

        # 2. Intent Classification & Entity Extraction
        analysis, response_text = await self.process_text_turn(db, user, text_query, session_context)

        # 4. Text to Speech
        audio_response = await tts_service.synthesize(response_text)

        result = {
            "query": text_query,
            "intent": analysis.get("intent"),
            "response_text": response_text,
            "fallback_used": bool(analysis.get("fallback_used", False)),
            "fallback_reason": analysis.get("fallback_reason"),
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
