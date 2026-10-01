# Naviora AI Deployment Guide

## One-Command Launch
To deploy the entire Naviora AI ecosystem (Backend, Database, Cache, Spatial Engine), run:
```bash
docker-compose up -d --build
```

The API is available at `http://localhost:8000`, API documentation at
`http://localhost:8000/docs`, and the admin console at `http://localhost:8080`.

## 🛠 Pre-requisites
1.  **Docker Desktop:** Compose requires Docker Engine with at least 4 GB available memory.
2.  **Environment:** Copy `.env.example` to `.env`, replace `SECRET_KEY`, and configure the database/service URLs.
3.  **AI services:** Ollama, Whisper, and Piper are optional for basic API operation but required for voice orchestration.

## 🏗 High-Availability Architecture
- **Web Layer:** FastAPI running via Uvicorn with GZip and TrustedHost middlewares.
- **Data Layer:** PostgreSQL 15 with **PostGIS** for high-precision indoor tracking.
- **Intelligence Layer:** Multi-agent orchestration via async HTTP to local LLM endpoints.

## 🏥 Clinical Setup
On first launch, the system automatically:
1. Apply migrations with `docker compose exec backend alembic upgrade head`.
2. Seed clinical departments with `docker compose exec backend python -m app.db.init_db`.
3. Verify the deployment with `curl http://localhost:8000/health`.

## 📱 Mobile Distribution
The React Native app is configured for Expo. To build for production:
```bash
cd frontend
npx expo start
```

## CI

GitHub Actions runs backend compilation/tests, mobile TypeScript checks, and the
admin production build on pushes to `main` and pull requests.
