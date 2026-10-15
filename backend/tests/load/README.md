# Backend load test

The Locust users authenticate with real, pre-provisioned test accounts and operate on a real backend and database. Do not point this workload at production. Provide IDs for existing records and tokens for accounts with the matching roles; no fixture data is created by Locust.

Required environment variables:

- `LOCUST_PATIENT_TOKEN`
- `LOCUST_STAFF_TOKEN`
- `LOCUST_EMERGENCY_TOKEN`
- `LOCUST_DOCTOR_ID`
- `LOCUST_DEPARTMENT_ID`
- `LOCUST_APPOINTMENT_ID`
- `LOCUST_APPOINTMENT_TIMES` — comma-separated, real future appointment slots with one unique slot per virtual patient
- `LOCUST_EMERGENCY_LOCATION`

Run the requested 500-user workload from `backend/`:

```powershell
locust -f tests/load/locustfile.py --host http://localhost:8000 --users 500 --spawn-rate 20 --run-time 5m --headless
```

For a local smoke check, use 50 users for 60 seconds:

```powershell
locust -f tests/load/locustfile.py --host http://localhost:8000 --users 50 --spawn-rate 10 --run-time 60s --headless
```

Record p50, p95, p99, and error rate from Locust's final summary. No backend was available for the smoke check during Phase 8 authoring, so results are **NOT VERIFIED — needs running backend**. No latency or error-rate results are claimed.
