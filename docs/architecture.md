# Naviora AI Architecture

This describes the checked-in application and Render deployment configuration. It is not a claim that every integration is configured in production.

## System view

```mermaid
flowchart LR
  Patient[Patient Expo app] -->|HTTPS REST| API[FastAPI API]
  Staff[Staff Expo app] -->|HTTPS REST| API
  Admin[Admin screens] -->|HTTPS REST| API
  Patient <-->|WebSocket events| API
  Staff <-->|WebSocket events| API
  API --> DB[(PostgreSQL / configured SQL database)]
  API --> Redis[(Redis: queue, voice pending state, realtime broker)]
  API --> LLM[Ollama / configured language model]
  API --> STT[Speech recognition service]
  API --> TTS[Speech synthesis service]
  API --> Push[Firebase Cloud Messaging, when configured]
  API --> Monitor[Sentry / Prometheus instrumentation]
  API --> Reminder[Database-backed feedback reminder loop]
  Reminder --> DB
  Reminder --> Push
```

## Runtime components

- **Frontend:** Expo / React Native source under `frontend/src`. Patient, staff, and admin navigators select role-specific screens. Mobile audio capture is implemented in the patient Voice Assistant.
- **API:** FastAPI routes under `backend/app/api/v1/endpoints`, mounted under `/api/v1`. Request validation uses Pydantic; database work uses SQLAlchemy async sessions.
- **Database:** SQLAlchemy models under `backend/app/models`; Alembic migrations under `backend/alembic/versions`. Production startup in `render.yaml` applies `alembic upgrade head` before starting Uvicorn.
- **Redis:** Used by voice pending/clarification state and realtime queue/event coordination. Redis is a required runtime dependency for those workflows.
- **Voice:** Audio is transcribed by the STT service; intent is classified by HospitalBrain with a rule-based fallback when the LLM is unavailable. Appointment proposals require an explicit confirmation and pending state has a short Redis TTL.
- **Realtime:** WebSocket manager broadcasts patient and staff queue updates; Redis coordinates events between API workers.
- **Feedback reminders:** Completed appointments create a persistent reminder due one hour later. API workers poll the database and dispatch through the existing push service; the reminder row survives process restart.
- **Observability:** `/health`, `/health/detailed`, `/ready`, and `/metrics` provide operational signals. Sentry and Firebase depend on production configuration.

## Main patient booking flow

```mermaid
sequenceDiagram
  participant P as Patient app
  participant A as FastAPI
  participant R as Redis
  participant L as LLM / rule fallback
  participant D as SQL database
  P->>A: POST /api/v1/voice/process (audio or text)
  A->>L: Transcribe/classify request
  L-->>A: Intent and extracted details
  A->>R: Store short-lived booking proposal
  A-->>P: Ask patient to confirm details
  P->>A: Confirm or cancel
  A->>D: Recheck availability and persist appointment
  A->>R: Clear pending proposal
  A-->>P: Booking result
```

## Deployment boundary

`.github/workflows/test.yml` runs backend tests with a Redis service and frontend type/unit tests. On successful Test workflow completion for `main`, `.github/workflows/deploy.yml` calls the Render deploy hook and polls the configured health endpoint. The Render service plan, secrets, external providers, and mobile store release are outside this repository's architecture diagram and must be verified separately.
