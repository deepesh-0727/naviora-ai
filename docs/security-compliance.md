# Security and Compliance Summary

**Status:** Repository evidence summary only. This is not legal advice, a security audit, or a claim of HIPAA, DPDP Act, or other certification. A hospital and qualified counsel/security reviewers must verify the production configuration and applicable obligations before real patient use.

## Controls present in the repository

- **Authentication and role boundaries:** Access tokens are checked by API middleware; admin and staff namespaces enforce role classes. Route dependencies add narrower role checks where implemented. See `backend/app/main.py` and `backend/app/api/deps.py`.
- **Password handling:** Authentication uses the project security utilities and hashed passwords; passwords are not stored in clear text. See `backend/app/core/security.py` and `backend/app/services/auth_service.py`.
- **Encryption at rest for selected data:** Patient names/contact/history and voice transcripts/response text use Fernet-backed SQLAlchemy types. Push tokens are now stored as encrypted values in `registered_devices`; existing hash-only device records need to register again to enable push delivery. See `backend/app/core/encryption.py`, `backend/app/models/patient.py`, `backend/app/models/voice_interaction.py`, and `backend/app/models/operations.py`.
- **Audit and request tracing:** Audit middleware records request activity and request IDs are attached to logs/responses. Scope and completeness must be checked against each hospital's audit requirements. See `backend/app/middleware/audit.py` and `backend/app/middleware/request_id.py`.
- **Transport and deployment:** Production uses the Render HTTPS host configured outside source control. GitHub Actions gates deployment on tests and checks backend health. Confirm TLS configuration, domain, headers, and actual deployment settings independently.
- **Backups and incident response:** The repository includes [backup/restore](backup-restore-runbook.md) and [incident response](compliance/incident-response.md) materials. A successful restore drill and current contact list are operational evidence, not established by code alone.

## Important gaps and required review

- No HIPAA or DPDP certification is claimed. A technical control in the codebase does not by itself establish legal compliance.
- Confirm whether each party is a Data Fiduciary, processor, covered entity, or business associate for the intended deployment. Execute the appropriate data-processing/BAA or equivalent agreements after legal review.
- Verify lawful basis, patient notice and consent/withdrawal requirements, purpose limitation, patient rights workflows, retention/deletion, breach timelines, localization/transfer rules, subprocessors, and backup/telemetry handling with qualified counsel.
- Perform a production threat model, independent security assessment, dependency review, access review, encryption-key lifecycle review, and penetration test. Confirm secrets, database/backups, Redis, Sentry, and push provider configuration in their consoles.
- Confirm push tokens and voice/health content are handled under the hospital's approved notice, retention, access, and vendor agreements. Do not use real patient data in demo or training environments without explicit approval and safeguards.
- Confirm the emergency workflow has an operational human response and a phone fallback. The application is not an emergency service and must not be the sole response channel.

## Source documents

- [DPDP checklist](compliance/dpdp-checklist.md)
- [HIPAA checklist](compliance/hipaa-checklist.md)
- [Data retention plan](compliance/data-retention.md)
- [Incident response plan](compliance/incident-response.md)
- [Deployment runbook](deployment-runbook.md)
