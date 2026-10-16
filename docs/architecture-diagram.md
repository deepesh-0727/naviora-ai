# Final Architecture Diagram

The diagram reflects the current repository wiring. External services are conditional on deployment configuration.

```mermaid
flowchart TB
  subgraph Clients[Expo / React Native clients]
    P[Patient app\nvoice, booking, queue, feedback, SOS]
    S[Staff app\nqueue, clinical and emergency screens]
    A[Admin screens\noperations and pilot metrics]
  end

  subgraph Render[Render backend service]
    GW[FastAPI\nJWT and role checks]
    WS[WebSocket manager]
    FB[Feedback reminder poller]
  end

  P -->|HTTPS REST| GW
  S -->|HTTPS REST| GW
  A -->|HTTPS REST| GW
  P <-->|Queue and notification events| WS
  S <-->|Queue and emergency events| WS
  GW -->|SQLAlchemy async| SQL[(Configured SQL database)]
  GW -->|Queue and expiring voice state| R[(Redis)]
  WS <-->|Cross-worker event coordination| R
  GW -->|Speech requests| STT[Speech recognition]
  GW -->|Intent classification| LLM[Ollama / configured LLM]
  GW -->|Spoken response when enabled| TTS[Speech synthesis]
  GW -->|Encrypted token| TOK[Registered device tokens]
  FB -->|Due reminders and status| SQL
  FB -->|Push attempt| FCM[Firebase Cloud Messaging]
  GW --> OBS[Sentry and Prometheus instrumentation]
```

## Data paths

- Booking and queue state are persisted in the configured SQL database. Redis holds short-lived voice confirmation state and coordinates live updates.
- Patient voice transcripts and selected patient information are encrypted through project SQLAlchemy types; see [Security and Compliance](security-compliance.md).
- Feedback reminders are persisted with due times and polled by application workers. Push delivery requires an active registered device token and Firebase configuration; the in-app notification is also stored.
- Tests use SQLite for most isolated unit cases and an explicitly configured Redis service for integration cases.
