import os
from functools import lru_cache
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from faster_whisper import WhisperModel

app = FastAPI(title="Naviora Whisper STT", docs_url=None, redoc_url=None)


@lru_cache(maxsize=1)
def model() -> WhisperModel:
    name = os.getenv("WHISPER_MODEL", "small")
    device = os.getenv("WHISPER_DEVICE", "cuda")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "float16" if device == "cuda" else "int8")
    return WhisperModel(name, device=device, compute_type=compute_type)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ready", "model": os.getenv("WHISPER_MODEL", "small")}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str | None = Form(default=None)) -> dict[str, str | None]:
    if not (file.content_type or "").startswith("audio/"):
        raise HTTPException(status_code=415, detail="Upload a supported audio file.")
    payload = await file.read(25 * 1024 * 1024 + 1)
    if len(payload) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio upload exceeds 25 MB.")
    if not payload:
        raise HTTPException(status_code=400, detail="Audio upload is empty.")
    try:
        with NamedTemporaryFile(suffix=".audio") as temp:
            temp.write(payload)
            temp.flush()
            segments, info = model().transcribe(temp.name, language=language, vad_filter=True)
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Speech recognition is unavailable.") from exc
    return {"text": transcript, "language": info.language}
