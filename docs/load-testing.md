# Load testing

## Read-only health smoke test

Start the backend locally with its safe local/test configuration. Run this from the repository root in PowerShell:

```powershell
cd backend
.\venv\Scripts\python.exe -m locust `
  -f tests/load/health_smoke_locustfile.py `
  --headless --host http://127.0.0.1:8000 `
  --users 10 --spawn-rate 10 --run-time 10s
```

The dedicated smoke user only calls `GET /health`, checks the `200` status and `{"status":"ok"}` body, prints success/failure counts, and exits nonzero if there were no requests or the error rate is at least 1%. It does not authenticate or change database records. Run it against a local service, not production. A passing local smoke run proves only that the local liveness endpoint survived this short load; it does not measure database, Redis, AI, or production capacity.

## Authenticated workflow load test

`backend/tests/load/locustfile.py` models patient, staff, and emergency workflows using real test-account access tokens. It can create appointments, change queue state, and submit SOS events. Use a disposable local/staging database and test accounts only. Provision the IDs, tokens, appointment times, and emergency payload values required by the file in the process environment, then run a baseline such as:

```powershell
cd backend
.\venv\Scripts\python.exe -m locust `
  -f tests/load/locustfile.py `
  --host http://127.0.0.1:8000 `
  --users 50 --spawn-rate 5 --run-time 2m
```

Never paste tokens or patient data into shell history, CI logs, or reports. Reset the disposable data after each run.

## Pilot targets and reporting

The initial target at 50 concurrent users is p50 below 100 ms, p95 below 200 ms, p99 below 500 ms, and an error rate below 1%. These are targets, not measured results or a production capacity guarantee. Record the tested commit, environment, instance size, test duration, number of users, request count, error rate, p50/p95/p99, and any rate limits or dependency failures. Mark a target unverified until a run against an identified non-production environment produces evidence.
