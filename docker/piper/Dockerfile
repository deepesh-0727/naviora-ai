# Piper TTS Service
# Wraps rhasspy/wyoming-piper with a lightweight HTTP bridge
# so tts_service.py can call GET /say?text=... and receive WAV bytes

FROM python:3.11-slim

WORKDIR /app

# Install Wyoming Piper + HTTP shim dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    wyoming-piper \
    fastapi \
    uvicorn \
    httpx \
    python-multipart

# Copy the HTTP shim that translates GET /say → Wyoming protocol
COPY piper_http_bridge.py .

EXPOSE 10200

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:10200/health || exit 1

CMD ["uvicorn", "piper_http_bridge:app", "--host", "0.0.0.0", "--port", "10200"]
