# Developer Onboarding

## Prerequisites

- Git
- Python 3.11 (the backend CI workflow uses 3.11)
- Node.js 18 and npm (the frontend CI workflow uses Node 18)
- A local PostgreSQL database for full backend development, and Redis for queue, voice pending state, and integration tests
- A configured `.env` containing the required database, signing, encryption, and provider settings; never commit secrets

## Clone and install

```bash
git clone <repository-url>
cd NavioraAI
python -m venv backend/venv
# Activate the virtual environment for your shell.
python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
cd frontend
npm ci --legacy-peer-deps
```

Configure local environment variables using the examples in `backend/app/core/config.py` and the deployment configuration. Set a valid Fernet `ENCRYPTION_KEY`; do not copy production keys into local development. Start PostgreSQL and Redis with isolated development data.

## Run locally

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm start
```

The backend OpenAPI document is available at `/api/v1/openapi.json` and the interactive docs at `/docs`. Review the [API reference](api.md), [architecture](architecture.md), and [deployment runbook](deployment-runbook.md).

## Verify changes

Backend tests use an isolated SQLite database for unit tests and a configured real Redis service for Redis-backed integration tests. Set `NAVIORA_TEST_REDIS_URL` to a dedicated test Redis instance; do not point destructive test code at shared or production Redis.

```bash
cd backend
python -m pytest
```

Frontend verification:

```bash
cd frontend
npx tsc --noEmit
npm test -- --ci
```

Install and run the repository's pre-commit hooks with `pre-commit install` and `pre-commit run --all-files`.

## First change and review

1. Start from an up-to-date branch and create a focused feature branch.
2. Read relevant endpoint, schema, model, and migration code before changing behavior.
3. Add or update tests for the change. Add an Alembic migration for schema changes and verify the chain.
4. Run the relevant backend/frontend checks and inspect `git diff` for secrets, patient data, generated output, and unrelated edits.
5. Open a pull request with purpose, behavior, test evidence, migration/deployment notes, and known limitations. Do not include real patient data in examples or screenshots.
6. Merge only after required CI and review checks pass. Production deployment is triggered by a successful Test workflow on `main`.

## Troubleshooting

- **Redis tests fail:** Check `NAVIORA_TEST_REDIS_URL`, Redis reachability, and that it points to a disposable test database.
- **Database migration fails:** Stop; preserve logs and data. Do not manually edit `alembic_version` or downgrade production without an approved recovery plan.
- **Audio path fails:** Check microphone permission, file format, backend STT support, and provider configuration. Use the approved non-voice booking path during development.
- **Missing environment variables:** Check `backend/app/core/config.py`; use local-only values and never paste secrets into issues or chat.
