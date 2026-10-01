import logging
import base64
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api import deps
from app.db.session import get_db
from app.models.user import User
from app.services.voice.voice_orchestrator import voice_orchestrator
from app.services.voice.stt_service import stt_service
from app.services.voice.tts_service import tts_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Pydantic schemas ────────────────────────────────────────────────────────

class VoiceProcessResponse(BaseModel):
    query: str
    intent: Optional[str] = None
    response_text: str
    audio_response_b64: Optional[str] = None   # base64-encoded WAV bytes
    analysis: Optional[dict] = None
    session_id: Optional[str] = None


class TextQueryRequest(BaseModel):
    text: str
    session_id: Optional[str] = None


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "en_US-lessac-medium"


class SynthesizeResponse(BaseModel):
    text: str
    audio_b64: Optional[str] = None
    tts_available: bool


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/process",
    response_model=VoiceProcessResponse,
    summary="Full Voice Loop: Audio → STT → AI Brain → TTS Response",
    description=(
        "Accepts a WAV/OGG audio file. Runs the full pipeline: "
        "Speech-to-Text → Intent Classification → Action Execution → Text-to-Speech. "
        "Returns the text response and optionally base64-encoded audio."
    ),
)
async def process_voice_command(
    audio: UploadFile = File(..., description="WAV or OGG audio file from the mobile app"),
    session_id: Optional[str] = Form(None, description="Ongoing session context ID"),
    return_audio: bool = Form(True, description="Set to false to skip TTS and save latency"),
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Full voice command pipeline for the NavioraAI mobile app.
    Accepts raw audio and returns both text and audio responses.
    """
    # Validate file type
    content_type = audio.content_type or ""
    if not any(t in content_type for t in ["audio", "octet-stream"]):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Send audio/wav or audio/ogg.",
        )

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Received empty audio file.",
        )

    session_context = {"session_id": session_id or "default", "user_id": current_user.id}

    logger.info(
        f"[Voice/process] user={current_user.id} "
        f"session={session_id} audio_bytes={len(audio_bytes)}"
    )

    try:
        result = await voice_orchestrator.process_audio_command(
            db=db,
            user=current_user,
            audio_data=audio_bytes,
            session_context=session_context,
        )
    except Exception as exc:
        logger.error(f"[Voice/process] Orchestrator failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice processing service is temporarily unavailable.",
        )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result["error"],
        )

    # Encode audio response to base64 so it travels safely over JSON
    audio_b64: Optional[str] = None
    if return_audio and result.get("audio_response"):
        audio_b64 = base64.b64encode(result["audio_response"]).decode("utf-8")

    return VoiceProcessResponse(
        query=result.get("query", ""),
        intent=result.get("intent"),
        response_text=result.get("response_text", ""),
        audio_response_b64=audio_b64,
        analysis=result.get("analysis"),
        session_id=session_id,
    )


@router.post(
    "/process-text",
    response_model=VoiceProcessResponse,
    summary="Text Command (no audio) → AI Brain → Optional TTS Response",
    description=(
        "For devices that prefer to handle their own STT. "
        "Accepts a plain-text query and returns the AI response + optional audio."
    ),
)
async def process_text_command(
    body: TextQueryRequest,
    return_audio: bool = False,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Runs HospitalBrain intent classification + IntentExecutor on a pre-transcribed text query.
    Useful when the client handles STT locally (e.g., iOS SpeechRecognizer).
    """
    from app.agents.hospital_brain import HospitalBrain
    from app.services.intent_executor import intent_executor

    brain = HospitalBrain()
    session_context = {"session_id": body.session_id or "default", "user_id": current_user.id}

    logger.info(f"[Voice/text] user={current_user.id} query='{body.text[:80]}'")

    try:
        analysis = await brain.execute(body.text, session_context)
        response_text = await intent_executor.execute(db, current_user, analysis)
    except Exception as exc:
        logger.error(f"[Voice/text] Brain failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI processing unavailable.",
        )

    audio_b64: Optional[str] = None
    if return_audio:
        try:
            audio_bytes = await tts_service.synthesize(response_text)
            if audio_bytes:
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception:
            pass  # TTS failure is non-fatal

    return VoiceProcessResponse(
        query=body.text,
        intent=analysis.get("intent"),
        response_text=response_text,
        audio_response_b64=audio_b64,
        analysis=analysis,
        session_id=body.session_id,
    )


@router.post(
    "/transcribe",
    summary="Speech-to-Text only",
    description="Upload audio and get back the transcript. Does NOT run the AI brain.",
)
async def transcribe_audio(
    audio: UploadFile = File(..., description="WAV or OGG audio file"),
    language: Optional[str] = Form(None, description="ISO-639-1 language code, e.g. 'hi' for Hindi"),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Lightweight STT-only endpoint. Useful for live transcription UIs.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    logger.info(f"[Voice/transcribe] user={current_user.id} lang={language}")

    transcript = await stt_service.transcribe(audio_bytes, language=language)
    if transcript is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech recognition service unavailable. Check WHISPER_API_URL.",
        )

    return {"transcript": transcript, "language": language or "auto"}


@router.post(
    "/synthesize",
    summary="Text-to-Speech only",
    description="Convert text to speech. Returns base64-encoded WAV audio.",
    response_model=SynthesizeResponse,
)
async def synthesize_speech(
    body: SynthesizeRequest,
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Standalone TTS endpoint. Returns audio as base64 JSON so it plays
    in React Native via `expo-av` without a streaming server.
    """
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    logger.info(f"[Voice/synthesize] user={current_user.id} len={len(body.text)}")

    audio_bytes = await tts_service.synthesize(body.text, voice=body.voice)

    if audio_bytes is None:
        # Return graceful degradation — frontend will display the text instead
        return SynthesizeResponse(text=body.text, audio_b64=None, tts_available=False)

    return SynthesizeResponse(
        text=body.text,
        audio_b64=base64.b64encode(audio_bytes).decode("utf-8"),
        tts_available=True,
    )


@router.get(
    "/health",
    summary="Voice services health check",
)
async def voice_health():
    """
    Quick liveness check for Whisper and Piper sidecars.
    Returns status of each dependency without requiring auth.
    """
    from app.core.config import settings
    import httpx

    results = {}

    for name, url in [("whisper_stt", settings.WHISPER_API_URL), ("piper_tts", settings.PIPER_API_URL)]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(url.rstrip("/") + "/health")
                results[name] = "reachable" if r.status_code < 500 else "degraded"
        except Exception:
            results[name] = "unreachable"

    overall = "healthy" if all(v == "reachable" for v in results.values()) else "degraded"
    return {"status": overall, "services": results}
