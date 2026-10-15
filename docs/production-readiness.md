# Production readiness — Phase 10

**Status:** implementation is committed; production operations remain partially unverified. This checklist distinguishes code that exists from services and drills that have actually been configured or run.

## Readiness checklist

| Check | Status | Evidence or reason |
|---|---|---|
| Sentry DSN configured | TODO | The project context says `SENTRY_DSN` is empty. Startup logs that error tracking is disabled. The admin-only `/debug/sentry` returns 503 until Sentry is initialized. Local tests capture an event through an in-process test transport; delivery to a real Sentry project has not been verified. |
| Grafana connected to `/metrics` | TODO | The endpoint exports Prometheus text and tests assert the custom counters. `docs/monitoring.md` documents Alloy scraping and token handling. No Grafana Cloud account or live scrape has been confirmed. |
| Independent uptime monitor configured | TODO | `/health` and a 15-minute GitHub Actions workflow exist. An UptimeRobot or Better Stack monitor and alert destination are not configured in this repository. |
| Backup tested against a real scratch database | TODO | The backup command and encrypted archive tests exist, including a nonzero failure-path test. No real Postgres dump plus Redis RDB export was run. The local environment points to remote services; use a dedicated scratch database and disposable Redis before testing. |
| Restore drill completed | TODO | The runbook contains the steps and provisional RTO/RPO, but explicitly records that no drill was run. A successful drill must verify both restored Postgres data and Redis state. |
| Load test passed | TODO | A 10-user/10-second read-only `/health` smoke run passed with 823 requests and 0 errors. The authenticated 50-user workflow run and its performance targets have not been measured. |
| Custom domain live | ACCEPTED RISK | Use `naviora-backend-s6je.onrender.com` for the pilot. The custom-domain guide is ready, but no domain purchase or DNS cutover is confirmed. This status accepts the current Render hostname for pilot use; it does not claim `api.naviora.ai` is live. |
| SSL Labs A+ rating | TODO | No custom domain is live and no SSL Labs report was captured. Render-managed TLS is not evidence of an A+ rating. |
| Render paid plan / no sleep | ACCEPTED RISK | The pilot uses the free service tier. Free web services can spin down after inactivity and cold starts can take about a minute. This is accepted for the pilot; upgrade before a production service-level commitment. See [Render free instance limitations](https://render.com/docs/free). |
| HIPAA / DPDP compliance review | TODO | No legal, security, privacy, or operational compliance review is recorded. Passing tests and enabling infrastructure controls do not establish compliance. |

## Implemented and locally verified

- The public `/health/detailed` endpoint reports uptime, application version, and live Postgres, Redis, and configured AI-provider reachability. It uses a bounded, per-process rate limit so health reporting still works when Redis is down.
- `/debug/sentry` requires an admin role, returns 503 if Sentry is disabled or uninitialized, and generates a real SDK event when configured.
- `/metrics` tests assert Prometheus text output and `naviora_ws_active_connections`, `naviora_voice_requests_total`, and `naviora_emergency_triggers_total`.
- `.github/workflows/uptime.yml` checks `/health` every 15 minutes, retries three times, and opens a deduplicated GitHub issue on repeated failures. It has not yet had a scheduled production run verified.
- `docs/monitoring.md`, `docs/backup-restore-runbook.md`, `docs/custom-domain.md`, and `docs/load-testing.md` document setup and operational procedures.
- The last full backend run passed 194 tests with 72.51% coverage. The frontend suite passed 18 tests. The read-only local liveness smoke passed as recorded above.

## Pilot conditions

Before a real hospital pilot, assign an owner and date for each TODO. In particular, perform backup and restore against isolated disposable services, configure an independent uptime alert, verify Sentry event delivery, and complete the required privacy/compliance review. Do not use production patient data in load tests or backup drills.
