# Deployment Runbook

## Deployment path

Production backend deploys are configured through GitHub Actions and Render:

1. Push the approved commit to `main`.
2. `.github/workflows/test.yml` runs the full backend suite with a Redis service, then frontend TypeScript checks and unit tests.
3. `.github/workflows/deploy.yml` runs only after the `Test` workflow succeeds on `main`. It validates `RENDER_DEPLOY_HOOK` and `RENDER_BACKEND_URL`, calls the hook, and polls `/health` for up to five minutes.
4. Render runs the configured `startCommand`: change to `backend`, apply `alembic upgrade head`, then start Uvicorn with four workers.
5. Confirm the Deploy workflow is green. Then verify `/health`, `/health/detailed`, and the user-facing workflow affected by the release.

## Pre-deploy checks

- Confirm the change is committed to the intended branch and the working tree is clean.
- Review the migration chain with `cd backend; alembic heads` and inspect migrations for destructive or data-dependent operations.
- Confirm GitHub Actions secrets are present: `RENDER_DEPLOY_HOOK` and `RENDER_BACKEND_URL`. Runtime secrets are configured in Render, not this repository.
- Check that any new required environment variable is documented and configured before release.
- Ensure CI has a working Redis service for Redis-dependent tests.

## Post-deploy verification

- Check the `Test` and `Deploy` runs for the exact commit SHA.
- Request `GET https://<configured-backend-host>/health` and confirm success.
- Request `/health/detailed` and review dependency results; do not interpret liveness alone as full workflow verification.
- For a migration or workflow change, perform an approved smoke test with designated test accounts and non-production patient data where possible.
- Check Render logs and Sentry for new startup errors or elevated failures.

## Rollback

1. If health or the changed workflow fails, pause pilot use of that workflow and activate the documented manual process.
2. Identify the last known good commit and the first failing deploy by SHA and timestamp.
3. Revert the faulty commit in Git (`git revert <commit>`), push the revert to `main`, and let the normal Test then Deploy workflow run. Do not force-push `main`.
4. Verify the reverted build and affected health/workflow checks.
5. **Database caution:** application rollback does not reverse an Alembic migration. Do not run `alembic downgrade` against production without an approved data-preserving rollback plan and database backup. Prefer a forward corrective migration for additive schema changes.
6. Notify hospital contacts through the agreed incident channel, record impact and timeline, and keep the manual workflow active until recovery is verified.

## Secret and access handling

Do not place credentials in source, commit messages, screenshots, or incident tickets. Use GitHub Actions secrets for deploy hooks and Render environment settings for runtime configuration. Rotate any exposed credential and review deployment access after an incident. Backup and restore steps are in [Backup and Restore Runbook](backup-restore-runbook.md).
