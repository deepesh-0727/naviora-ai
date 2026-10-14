import os
from functools import lru_cache
from io import BytesIO

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from piper import PiperVoice

app = FastAPI(title="Naviora Piper TTS", docs_url=None, redoc_url=None)


@lru_cache(maxsize=2)
def load_voice(language: str) -> PiperVoice:
    variable = "PIPER_MODEL_HI" if language.lower().startswith("hi") else "PIPER_MODEL_EN"
    model_path = os.getenv(variable)
    if not model_path or not os.path.isfile(model_path):
        raise RuntimeError(f"A configured {variable} voice model is required.")
    return PiperVoice.load(model_path)


@app.get("/health")
async def health() -> dict[str, str]:
    configured = all(os.path.isfile(os.getenv(key, "")) for key in ("PIPER_MODEL_EN", "PIPER_MODEL_HI"))
    return {"status": "ready" if configured else "degraded"}


@app.get("/say")
async def say(text: str = Query(min_length=1, max_length=3000), voice: str = "en_US-lessac-medium") -> Response:
    if voice not in {"en_US-lessac-medium", "hi_IN-priyamvada-medium"}:
        raise HTTPException(status_code=422, detail="Unsupported voice selection.")
    try:
        language = "hi" if voice.startswith("hi_") else "en"
        output = BytesIO()
        load_voice(language).synthesize_wav(text, output)
        return Response(output.getvalue(), media_type="audio/wav")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Text-to-speech voice model is unavailable.") from exc
