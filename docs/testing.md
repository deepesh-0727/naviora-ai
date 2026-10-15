# Testing

## Local commands

Backend tests use the SQLite test database configured by `backend/tests/conftest.py`.
For Redis-backed integration journeys, start a dedicated test Redis database and set
`NAVIORA_TEST_REDIS_URL` to its URL. The integration fixtures flush that database
before and after each journey.

```powershell
python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
python -m pytest backend/tests
```

The root `pytest.ini` prints per-file coverage and enforces a 70% overall gate. CI
starts Redis and sets `NAVIORA_TEST_REDIS_URL`; local journey tests report an
explicit external-blocker skip when that variable is absent.

Frontend tests use Jest with `jest-expo@50` for the Expo SDK 50 app. From `frontend/`:

```powershell
npm ci --legacy-peer-deps
npx tsc --noEmit
npm test
```

Add tests under `frontend/__tests__/` with behavior-focused assertions. Avoid snapshots
and live network calls. Current tests cover the patient appointment, queue, emergency,
login, dashboard, authentication, API, and WebSocket flows. Several other hooks and
services do not yet have tests, so frontend-wide hooks/services coverage remains below
the 50% target.

## Coverage policy and current status

- Backend overall gate: 70%; the latest local run reached 71%.
- Backend services: the emergency service is at 100%, location service at 78%,
  and `queue_service.py` at 90%. `queue.py` is at 87%; appointments and doctors
  endpoints are at 97% and 95% respectively.
- Latest backend run: 172 passed, 8 skipped, with zero failures. The 8 skips are the
  Redis-dependent integration journeys that require a verified dedicated test Redis.
- Frontend Jest: 17 tests pass across 8 suites. In the current full hooks/services
  inventory, statement coverage is 21.75%; the modules exercised by the new tests
  individually range from 51% to 92%.
- Redis-backed patient, staff, emergency, RBAC, and realtime integration journeys are
  present but were skipped locally because no verified dedicated test Redis was available.
- The complete per-file backend coverage table is in `docs/phase8-coverage.txt`.
- Locust files are in `backend/tests/load/`. The 50-user, 60-second smoke run is
  `NOT VERIFIED — needs running backend`.

Do not lower coverage targets to make a failing gate pass. Add deterministic tests for
the uncovered service and endpoint paths, then rerun the full suites before considering
the targets met.
