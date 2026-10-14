# HIPAA Security Rule control mapping

**Review date:** 2026-10-15  
**Scope:** Repository evidence only. This is not a legal opinion, risk analysis, audit, or representation that Naviora AI or any deployment is HIPAA compliant. Applicability depends on the parties, data flows, and contracts. HHS explains that safeguards must be selected through an organization-specific risk analysis and maintained over time ([HHS Security Rule summary](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html)).

Status means only what this repository demonstrates: **Partial** means code contributes to a control but does not establish the complete organizational requirement; **Gap** means no adequate evidence was found in the repository; **Planned** means a later Phase 7 batch is expected to add an artifact, not that the safeguard is operational.

## General requirements — 45 CFR §164.306

| Standard | Repository evidence and current status | Gap / action |
|---|---|---|
| §164.306(a)-(e) General requirements: ensure confidentiality, integrity, and availability; protect against reasonably anticipated threats and impermissible uses/disclosures; ensure workforce compliance; select and maintain reasonable safeguards based on risk | **Partial:** authentication/RBAC, field encryption, selected audit logging, rate limiting, security headers, and application tests exist ([backend/app/core/rbac.py:13-61](../../backend/app/core/rbac.py#L13), [backend/app/core/encryption.py:10-45](../../backend/app/core/encryption.py#L10), [backend/app/middleware/audit.py:14-62](../../backend/app/middleware/audit.py#L14), [backend/app/core/middleware.py:42-53](../../backend/app/core/middleware.py#L42)). | **P0:** organization-level risk analysis, safeguards maintenance, workforce accountability, and evidence of availability/integrity controls are not established by these code mechanisms. |

## Administrative safeguards — 45 CFR §164.308

| Standard / implementation specification | Repository evidence and current status | Gap / action |
|---|---|---|
| §164.308(a)(1) Security management process: risk analysis, risk management, sanctions, information-system activity review | **Partial:** role checks and selected access audit records exist in [backend/app/core/rbac.py:13-61](../../backend/app/core/rbac.py#L13) and [backend/app/middleware/audit.py:11-62](../../backend/app/middleware/audit.py#L11). | **P0:** conduct and approve an organization-wide ePHI risk analysis; track risks, owners, mitigations, sanctions, and recurring log reviews. Code is not evidence that these activities occur. |
| §164.308(a)(2) Assigned security responsibility | No named security official or assignment process was found. | **P1:** designate the security official and document authority, escalation, and coverage. |
| §164.308(a)(3) Workforce security: authorization/supervision, workforce clearance, termination procedures | **Partial:** application role boundaries are implemented in [backend/app/core/rbac.py:32-61](../../backend/app/core/rbac.py#L32) and [backend/app/main.py:90-135](../../backend/app/main.py#L90). | **P1:** document workforce onboarding, access approval, supervision, periodic review, and prompt termination/revocation. |
| §164.308(a)(4) Information access management: access authorization, establishment/modification, access review | **Partial:** authenticated user and role checks are enforced in [backend/app/api/deps.py:27-71](../../backend/app/api/deps.py#L27) and [backend/app/core/rbac.py:32-61](../../backend/app/core/rbac.py#L32). | **P1:** document minimum-necessary policy and workforce access approval/review. Emergency access procedures are not evidenced. |
| §164.308(a)(5) Security awareness and training: reminders, protection from malicious software, login monitoring, password management | No training, sanctions, or awareness tracking was found. | **P1:** establish training, completion records, security reminders, and workforce sanctions. |
| §164.308(a)(6) Security incident procedures: response/reporting and mitigation | This document set adds a response playbook in [incident-response.md](incident-response.md); application logs and audit records provide partial evidence in [backend/app/core/logging.py](../../backend/app/core/logging.py) and [backend/app/middleware/audit.py:14-62](../../backend/app/middleware/audit.py#L14). | **P0:** assign an incident lead, maintain a case register and evidence process, exercise the plan, and confirm applicable reporting duties with counsel. A written playbook alone does not show the procedure is operational. |
| §164.308(a)(7) Contingency plan: data backup, disaster recovery, emergency-mode operations, testing/revision, applications/data criticality analysis | **Partial:** encrypted PostgreSQL/Redis scripts and a runbook exist ([backend/scripts/backup_restore.py](../../backend/scripts/backup_restore.py), [docs/backup-restore-runbook.md](../backup-restore-runbook.md)); no successful backup/restore drill is evidenced. | **P0:** test and document backups; write organization-approved disaster-recovery and emergency-mode plans; classify critical systems; record drill results. RTO/RPO targets are not yet validated. |
| §164.308(a)(8) Evaluation | Tests exist, but no periodic organization-wide technical and nontechnical evaluation or approval record was found. | **P1:** schedule and document recurring evaluations and reassess after material changes. |
| §164.308(b) Business associate contracts and other arrangements | Vendor settings and service integrations exist, but repository code cannot establish executed BAAs. | **P0:** inventory vendors that create, receive, maintain, or transmit ePHI; determine BAA status and approve contracts before use. |

## Physical safeguards — 45 CFR §164.310

| Standard / implementation specification | Repository evidence and current status | Gap / action |
|---|---|---|
| §164.310(a) Facility access controls, including contingency operations, facility security plan, access validation, maintenance records | No evidence in application code; cloud facility controls are provider responsibilities and need contractual evidence. | **P1:** obtain provider assurance reports/contracts and define facility-access and contingency procedures for any organization-controlled locations. |
| §164.310(b) Workstation use | No workstation-use policy or inventory found. | **P1:** define approved use for devices accessing ePHI. |
| §164.310(c) Workstation security | No endpoint hardening, physical safeguards, or workstation access evidence found. | **P1:** define and verify endpoint controls. |
| §164.310(d) Device and media controls: disposal, media reuse, accountability, data backup | No device/media procedures found in code. | **P1:** maintain media inventory, secure transfer and disposal, sanitization evidence, and backup-media controls. |

## Technical safeguards — 45 CFR §164.312

| Standard / implementation specification | Repository evidence and current status | Gap / action |
|---|---|---|
| §164.312(a) Access control: unique user identification, emergency access, automatic logoff, encryption/decryption | **Partial:** users have database IDs and JWT subject claims; access-token expiry defaults to 24 hours and refresh-token expiry to 7 days ([backend/app/models/user.py:12-25](../../backend/app/models/user.py#L12), [backend/app/core/security.py:11-42](../../backend/app/core/security.py#L11), [backend/app/core/config.py:20-21](../../backend/app/core/config.py#L20)). Selected patient columns use Fernet field encryption ([backend/app/models/patient.py:17-26](../../backend/app/models/patient.py#L17), [backend/app/core/encryption.py:10-45](../../backend/app/core/encryption.py#L10)). | **P0:** implement/document emergency access and inactivity logoff. Database/provider encryption at rest is not verified. Several personal fields remain unencrypted; see [backend/app/models/patient.py:18-26](../../backend/app/models/patient.py#L18). |
| §164.312(b) Audit controls | **Partial:** sensitive patient/staff/admin reads and writes create audit rows in [backend/app/middleware/audit.py:11-62](../../backend/app/middleware/audit.py#L11), stored in [backend/app/models/hospital.py:8-21](../../backend/app/models/hospital.py#L8). | **P1:** verify coverage of all ePHI access paths (including WebSockets, exports, background work, and direct database operations), protect log integrity, and perform documented review. No log-retention enforcement exists. |
| §164.312(c) Integrity: policies and mechanisms against improper alteration/destruction | Database constraints and application validation exist, but no comprehensive ePHI integrity verification or tamper detection is evidenced. | **P1:** document integrity controls, privileged-change monitoring, backup validation, and recovery checks. |
| §164.312(d) Person/entity authentication | **Partial:** JWT validation and password hashing are implemented in [backend/app/api/deps.py:27-70](../../backend/app/api/deps.py#L27) and [backend/app/core/security.py:45-48](../../backend/app/core/security.py#L45). | **P1:** review MFA, privileged access, service identities, and account lifecycle against risk. |
| §164.312(e) Transmission security: integrity controls and encryption | **Partial:** deployment configuration points to Render services and the app emits HSTS ([backend/app/core/middleware.py:42-53](../../backend/app/core/middleware.py#L42), [render.yaml:1-28](../../render.yaml#L1)). | **P0:** verify TLS termination, redirect/plaintext behavior, internal service links, certificate lifecycle, and database/Redis transport encryption in deployed environments. The code does not force HTTPS; wildcard CORS is configured in [backend/app/main.py:159-166](../../backend/app/main.py#L159). |

## Organizational requirements and documentation — §§164.314, 164.316

| Requirement | Repository evidence and current status | Gap / action |
|---|---|---|
| §164.314(a) Business associate contracts | Not verifiable from source code. | **P0:** execute and maintain required written assurances with relevant business associates and subcontractors. |
| §164.314(b) Group health plan requirements | Applicability and plan documentation are not established by this repository. | **P2:** determine applicability with counsel and document any required plan-document amendments and certifications. |
| §164.316(a)-(b) Policies/procedures and documentation: maintain, make available, update, and retain required documentation | This checklist and the incident/backup runbooks are draft technical artifacts, not evidence of approval or operation. | **P1:** appoint owners, approve/version policies, train affected workforce, retain required documentation for the applicable period, and record review dates. HIPAA’s six-year documentation rule is not a blanket six-year retention rule for all patient records or every audit log; validate each record class with counsel. |

## Specific repository observations

- **Encryption:** field-level Fernet handling covers patient first/last name, allergies, emergency contacts, and medical history. Date of birth, gender, blood group, insurance fields, and user contact fields are not encrypted by those ORM types ([backend/app/models/patient.py:17-26](../../backend/app/models/patient.py#L17), [backend/app/models/user.py:12-25](../../backend/app/models/user.py#L12)). This does not prove database-volume encryption.
- **Transport:** HSTS is emitted, but TLS is a deployment property and must be verified at every hop; the app does not redirect HTTP to HTTPS ([backend/app/core/middleware.py:42-53](../../backend/app/core/middleware.py#L42)).
- **Audit:** the middleware records selected paths, not a complete demonstrated inventory of all ePHI activity ([backend/app/middleware/audit.py:11-62](../../backend/app/middleware/audit.py#L11)).
- **Retention:** the database models have creation timestamps but no retention/deletion schedule or pruning process ([backend/app/models/hospital.py:8-21](../../backend/app/models/hospital.py#L8), [backend/app/models/patient.py:29-30](../../backend/app/models/patient.py#L29)).

## Prioritized actions

1. **P0:** approved risk analysis; vendor/BAA inventory; testable contingency plan and successful restore drill; verify deployment TLS, network restrictions, and encryption; establish incident ownership and reporting workflow.
2. **P1:** workforce lifecycle/training, emergency access and session controls, full ePHI audit inventory/review, integrity monitoring, approved policies, endpoint and physical safeguards.
3. **P2:** assess group-health-plan applicability and document disposition.

## Regulatory references

- [HHS — Summary of the HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html)
- [HHS — The Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [HHS — Security Rule administrative safeguards and contingency planning](https://www.hhs.gov/sites/default/files/ocr/privacy/hipaa/administrative/securityrule/adminsafeguards.pdf)
