# Data retention and deletion policy baseline

**Review date:** 2026-10-15  
**Status:** Proposed policy targets below are not currently enforced by application code. Adopt them only after legal, clinical-record, contract, and backup-retention review. Do not treat a target as an implemented control.

## Retention schedule

| Data class | Proposed baseline | What the repository actually does | Action |
|---|---|---|---|
| Patient PII and clinical records | 7 years from the last care/service event as a provisional default; configurable by jurisdiction, record type, and legal hold | No configurable retention setting, automatic expiry, or deletion job was found. Patient and audit models define creation timestamps but no retention policy ([backend/app/models/patient.py:29-30](../../backend/app/models/patient.py#L29), [backend/app/models/hospital.py:8-21](../../backend/app/models/hospital.py#L8)). | **P0:** legal/clinical owner approves a record-class schedule; implement deletion or anonymization across database, processor, and backup copies, with legal holds and verified completion. Seven years is a provisional product target, not a universal HIPAA or DPDP statutory period. |
| Audit/security/processing logs | Internal target: retain at least 6 years, subject to a documented purpose and lawful deletion schedule | Audit rows are created for selected API access but there is no purge/retention job ([backend/app/middleware/audit.py:14-62](../../backend/app/middleware/audit.py#L14), [backend/app/models/hospital.py:8-21](../../backend/app/models/hospital.py#L8)). | **P0:** determine record category and applicable law. HIPAA’s six-year documentation rule applies to required Security Rule documentation; it is not automatically a six-year mandate for every audit event. DPDP Rules 6(1)(e) and 8(3) specify one-year retention for defined security/processing logs and purposes, scheduled to commence 13 May 2027; implement the longest applicable approved requirement, not an unexamined blanket rule. |
| Access and refresh tokens | Internal target: no more than 30 days for token-related data; revoke on logout/account closure where supported | Defaults are 24-hour access tokens and 7-day refresh tokens ([backend/app/core/config.py:20-21](../../backend/app/core/config.py#L20), [backend/app/core/security.py:11-42](../../backend/app/core/security.py#L11)); refresh records store an expiry ([backend/app/api/v1/endpoints/auth.py:57-68](../../backend/app/api/v1/endpoints/auth.py#L57)). The 30-day target is not the current setting. | **P1:** document purpose/expiry and verify cleanup/revocation of expired refresh rows. |
| OTPs | Patient OTP: 5 minutes; staff/clinical roles: 3 minutes; admin roles: 2 minutes | Role-specific TTLs are stored in Redis ([backend/app/services/otp_service.py:11-21](../../backend/app/services/otp_service.py#L11), [backend/app/services/otp_service.py:57-89](../../backend/app/services/otp_service.py#L57)). | **P2:** keep TTL values aligned with the approved authentication policy and test expiry in the configured Redis service. |
| Password-reset tokens | 15 minutes | Redis expiry is set to 900 seconds ([backend/app/api/v1/endpoints/auth.py:232-250](../../backend/app/api/v1/endpoints/auth.py#L232)). | **P2:** confirm expiry and revocation behavior in production Redis. |
| Backup archives | 30 days local/S3 retention target after Phase 7 backup tooling lands | No successful production or local backup/restore drill is evidenced at this point in the phase. | **P0:** retain encrypted backups in a separate failure domain, enforce 30-day lifecycle, and test restoration. Batch 6 scripts/runbook must not be treated as proof until a drill is completed. |

## Operating rules

1. Classify each dataset and record the purpose, owner, source, processors, location, legal basis, retention trigger, and deletion mechanism.
2. Keep legal holds and healthcare record obligations separate from user account deletion. A deletion request may require erasing or restricting some data while preserving records required by another law.
3. Include replicas, caches, telemetry, exports, and processors in deletion design. Document backup expiry and restoration behavior so deleted data is not silently reintroduced.
4. Record deletion jobs, errors, exceptions, and approvals without logging the deleted personal data itself.
5. Reassess the schedule when law, contracts, provider regions, or processing purposes change.

## Sources

- Repository references above.
- [HIPAA Security Rule summary — HHS](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html)
- [DPDP Rules, 2025 — Gazette notification](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf)
- [DPDP Act commencement notification — Gazette of India](https://egazette.gov.in/WriteReadData/2025/267647.pdf)
