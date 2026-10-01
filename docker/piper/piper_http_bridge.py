"""
piper_http_bridge.py
────────────────────
Lightweight FastAPI HTTP bridge that accepts GET/POST /say requests
and forwards them to Wyoming Piper, returning raw WAV audio bytes.

This is deployed as the Piper TTS service on Render / docker-compose.
The backend's tts_service.py calls: GET /say?text=...&voice=en_US-lessac-medium
"""

import asyncio
import io
import logging
import os
import subprocess
import tempfile
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import Response

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Naviora Piper TTS Bridge",
    description="HTTP wrapper around wyoming-piper for Text-to-Speech synthesis",
    version="1.0.0",
)

PIPER_VOICE = os.getenv("PIPER_VOICE", "en_US-lessac-medium")
VOICES_DIR = os.getenv("VOICES_DIR", "/data/voices")


@app.get("/health")
async def health():
    return {"status": "ok", "voice": PIPER_VOICE}


@app.get(
    "/say",
    response_class=Response,
    responses={200: {"content": {"audio/wav": {}}}},
    summary="Synthesize text to WAV audio",
)
async def say(
    text: str = Query(..., description="Text to synthesize"),
    voice: Optional[str] = Query(None, description="Piper voice model name"),
):
    """
    Accepts plain text and returns WAV audio bytes using Piper TTS.
    Called by backend/app/services/voice/tts_service.py
    """
    selected_voice = voice or PIPER_VOICE

    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        audio_bytes = await _synthesize(text, selected_voice)
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as exc:
        logger.error(f"Piper synthesis failed: {exc}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"TTS synthesis failed: {exc}")


async def _synthesize(text: str, voice: str) -> bytes:
    """Run piper CLI and capture WAV output."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_file:
        out_path = out_file.name

    cmd = [
        "python", "-m", "wyoming_piper",
        "--piper", "piper",
        "--voice", voice,
        "--voices-dir", VOICES_DIR,
        "--output-file", out_path,
        "--text", text,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"Piper exited {proc.returncode}: {stderr.decode()}")

    with open(out_path, "rb") as f:
        return f.read()
