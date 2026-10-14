# Backup and restore runbook

**Owner:** Operations lead (to be assigned)  
**Review date:** 2026-10-15  
**Targets:** provisional RTO 30 minutes; provisional RPO 5 minutes. These targets have not been measured or achieved by a restore drill.

## What the scripts do

- `backend/scripts/backup.ps1` / `backend/scripts/backup.sh` call the shared Python implementation to create a plain PostgreSQL dump and a Redis RDB snapshot, add a manifest with a `public.users` row count, compress the files, and encrypt the archive with a dedicated Fernet key.
- If `AWS_ACCESS_KEY_ID` is set, the backup uploads to `BACKUP_S3_BUCKET` (and optional `BACKUP_S3_PREFIX`) using AWS CLI server-side encryption. Without that variable, it writes to `BACKUP_DIR`, defaulting to `backend/backups/`. Backups older than 30 days are pruned in that destination.
- `backend/scripts/restore.ps1 <archive>` / `backend/scripts/restore.sh <archive>` require a dedicated empty scratch PostgreSQL database in `RESTORE_DATABASE_URL`, a stopped local Redis data directory in `REDIS_DATA_DIR`, and a matching `BACKUP_ENCRYPTION_KEY`. Remote SQL targets are refused by default; `RESTORE_ALLOW_REMOTE=YES` is required for a remote scratch database. Restore refuses a non-empty SQL target and a Redis endpoint that is not loopback or appears to be running. It validates the Redis RDB before installing it.
- PostgreSQL and Redis are external services; the scripts do not fabricate success. Missing utilities, credentials, keys, unsupported managed Redis RDB export, query failures, invalid archives, or row-count mismatch return non-zero.

## One-time setup

1. Install PostgreSQL client utilities (`pg_dump`, `psql`) and Redis utilities (`redis-cli`, `redis-check-rdb`) on the operator machine. Install backend Python dependencies and activate that environment before running the wrappers (`.venv\Scripts\Activate.ps1` in PowerShell or `source .venv/bin/activate` in Bash).
2. Configure `DATABASE_URL` and `REDIS_URL` in the process environment or `backend/.env`. Do not paste their values into tickets, shell history, or command output.
3. Generate a separate backup-encryption key using a trusted secret manager/workstation:

   ```powershell
   $env:BACKUP_ENCRYPTION_KEY = .\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   For Bash, use `export BACKUP_ENCRYPTION_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"`. These assignments keep the generated value out of terminal output; persist it directly in the secret manager using an approved secure workflow, then remove the temporary shell value.

   Store it as `BACKUP_ENCRYPTION_KEY` in the deployment/operator secret store, separately from database and application keys. Preserve a securely escrowed recovery copy; losing it makes archives unrecoverable. Never put the key in the backup archive or repository.
4. For S3, set `AWS_ACCESS_KEY_ID`, the matching AWS credentials/session configuration, and `BACKUP_S3_BUCKET`. The script uses S3 SSE-S3 by default; set `BACKUP_S3_SSE_KMS_KEY_ID` for SSE-KMS. Without AWS access-key configuration, backups go to the local destination.
5. For restore, provision a **new, empty scratch PostgreSQL database** and a stopped local Redis instance/data directory. Set `RESTORE_DATABASE_URL`, `REDIS_DATA_DIR`, and optionally `REDIS_RESTORE_URL`/`REDIS_DUMP_FILENAME`. For a remote scratch database only, explicitly set `RESTORE_ALLOW_REMOTE=YES` after confirming the target.

## Backup procedure

1. Confirm the configured database and Redis are the intended source environment. A `.env` may point to remote production services.
2. Run from the repo root:

   ```powershell
   .\backend\scripts\backup.ps1
   ```

   or:

   ```bash
   ./backend/scripts/backup.sh
   ```

3. Confirm the command exits `0` and prints the archive destination. The filename is timestamped `naviora-backup-<UTC timestamp>.tar.gz.enc`.
4. Confirm the local archive exists or the S3 object is present. Keep the key separately. Do not treat object upload as a restore test.
5. The script prunes matching archives older than 30 days. Confirm the bucket lifecycle/backup location also meets organizational policy and access controls.

## Restore and verification procedure

1. Select an archive and provision an empty scratch PostgreSQL database plus a stopped, local Redis instance. Never point `RESTORE_DATABASE_URL` at production for a drill.
2. Set the variables from one-time setup and run:

   ```powershell
   .\backend\scripts\restore.ps1 D:\secure-backups\naviora-backup-<timestamp>.tar.gz.enc
   ```

   or:

   ```bash
   ./backend/scripts/restore.sh /secure/backups/naviora-backup-<timestamp>.tar.gz.enc
   ```

3. Require exit code `0`. The script decrypts and validates the archive, refuses a populated SQL target, restores the dump, and compares `public.users` row count against the backup manifest. It validates the Redis RDB and installs it into the configured stopped Redis data directory.
4. Start Redis with that data directory. Confirm `PING`, inspect expected database/key state with an authorized operator, and check `/ready` against the scratch services. Record results and evidence without copying patient records into the report.
5. Record archive timestamp, source/target environment labels, start/end times, row-count comparison, Redis validation/startup, application readiness, errors, operators, and follow-up actions. Remove scratch data securely after approval.

## Duration and recovery objectives

- **Expected duration:** no measured estimate exists. For planning only, allow 30–120 minutes depending on database size, provider bandwidth, PostgreSQL version, Redis dataset, and manual provisioning; measure this during the first drill.
- **RTO target:** 30 minutes, **unverified**. This includes provisioning, restore, Redis restart, and application verification; the current manual process may exceed it.
- **RPO target:** 5 minutes, **unverified and not met by an on-demand script alone**. Meeting it requires an automated schedule or provider-supported continuous/PITR backup with tested recovery points. No scheduler or PITR configuration is created by these scripts.

## Drill record — 2026-10-15

**Result: NOT RUN; restore remains unverified.** The configured `backend/.env` points to remote Supabase (`aws-0-ap-southeast-1.pooler.supabase.com`) and Upstash Redis (`logical-dogfish-323868.upstash.io`), not a local development database. The operator environment lacks `pg_dump`, `psql`, `redis-cli`, and `redis-check-rdb`; there is no local scratch DB/data directory available. To avoid running an unverified drill against remote live services, no backup or restore command was run. This is an operational blocker, not a successful drill. Provision local scratch services, install the utilities, configure the separate backup key, and record a new drill before claiming recovery objectives.

## Failure handling

- Any non-zero exit means the backup/restore did not complete. Preserve the safe error message and investigate locally; tool stderr is intentionally suppressed because it may contain connection information.
- If Redis does not support RDB export (common for managed offerings), the backup fails rather than silently omitting Redis state. Obtain a provider-supported export/backup procedure and adapt only after validating its consistency and restore path.
- If the SQL restore succeeds but a later step fails, treat the scratch environment as partial; discard/recreate it before retrying. Do not switch the target to production to “finish” a drill.
