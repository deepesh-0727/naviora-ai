# Whisper STT Service
# Based on onerahmet/openai-whisper-asr-webservice
# Exposes OpenAI-compatible ASR at POST /asr
FROM onerahmet/openai-whisper-asr-webservice:latest

# Environment variables are injected by Render / docker-compose
# ASR_MODEL: tiny | base | small | medium | large
# ASR_ENGINE: openai_whisper | faster_whisper

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:9000/docs || exit 1
