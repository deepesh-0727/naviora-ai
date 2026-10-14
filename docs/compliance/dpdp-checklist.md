# India Digital Personal Data Protection (DPDP) checklist

**Review date:** 2026-10-15  
**Scope:** Repository evidence and a staged implementation plan. This is not legal advice or a certification of compliance. Confirm applicability, lawful processing grounds, sector-specific rules, and commencement with Indian counsel.

## Commencement and transfer rules

The DPDP Act, 2023 and DPDP Rules, 2025 have staged commencement. As of this review date, the 13 November 2025 notification schedules section 6(9) and section 27(1)(d), and Rule 4, for 13 November 2026; the main duties in Act sections 3–17 and Rules 3, 5–16, 22, and 23 are scheduled for 13 May 2027. Recheck for later notifications before relying on these dates ([Act commencement notification](https://egazette.gov.in/WriteReadData/2025/267647.pdf), [Rules 2025](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf)).

Section 16 does **not** itself impose blanket India-only storage. It permits the Central Government to restrict transfers to notified countries and preserves stricter requirements under other Indian laws. The DPDP Rules also impose specific requirements in defined cases. The repo’s Render service declarations use the Singapore region ([render.yaml:1-28](../../render.yaml#L1), [render.yaml:80-118](../../render.yaml#L80)); the production database URL is supplied as deployment configuration, so its actual Supabase region is not verifiable from this source tree. Confirm the actual database, backups, telemetry, subprocessors, and any sector-specific localization obligation before launch. See [DPDP Act §16](https://www.meity.gov.in/static/uploads/2024/02/Digital-Personal-Data-Protection-Act-2023-1.pdf) and the applicable Gazette notifications.

## Requirement mapping

| Act / Rules topic | Repository evidence and current status | Priority / action |
|---|---|---|
| §§4–5 lawful purpose and notice | Registration and patient-profile APIs exist ([backend/app/api/v1/endpoints/auth.py:70-120](../../backend/app/api/v1/endpoints/auth.py#L70), [backend/app/api/v1/endpoints/patients.py:156-241](../../backend/app/api/v1/endpoints/patients.py#L156)); no versioned notice, purpose registry, or proof of notice delivery was found. | **P0:** document each purpose and lawful basis, publish a clear notice in supported languages, and retain notice versions/evidence. |
| §6 consent and withdrawal; §7 certain legitimate uses | No consent capture, consent ledger, purpose-level preference, or comparable withdrawal workflow was found. | **P0:** build an auditable consent/withdrawal flow where consent is the basis; record the separate lawful basis for any legitimate use. The Act requires consent to be free, specific, informed, unconditional, unambiguous, affirmative, and limited to necessary data ([Act §6](https://www.meity.gov.in/static/uploads/2024/02/Digital-Personal-Data-Protection-Act-2023-1.pdf)). |
| §8 Data Fiduciary duties and processor responsibility | App-level RBAC, field encryption, logging, and environment secrets exist ([backend/app/core/rbac.py:13-61](../../backend/app/core/rbac.py#L13), [backend/app/core/encryption.py:10-45](../../backend/app/core/encryption.py#L10), [backend/app/middleware/audit.py:14-62](../../backend/app/middleware/audit.py#L14)). No processor register, data-processing agreements, or accountability record was found. | **P0:** identify the legal Data Fiduciary, map processors/subprocessors, contract for safeguards, and maintain an accountable processing inventory. |
| Rule 6 reasonable security safeguards | **Partial:** some PII fields are encrypted and selected access events are logged, but coverage is incomplete and log retention/review is not implemented ([backend/app/models/patient.py:17-26](../../backend/app/models/patient.py#L17), [backend/app/middleware/audit.py:14-62](../../backend/app/middleware/audit.py#L14)). | **P0:** implement an evidence-backed security program, processor controls, access reviews, monitoring, and tested backups. Rule 6 specifies security measures, access control, logs/monitoring, backups, and processor contract provisions. |
| Rule 7 personal-data breach intimation | A response playbook is in [incident-response.md](incident-response.md); no operational affected-principal/Board notification workflow or case evidence was found. | **P0:** designate accountable responders, build notification templates and a decision log, and test notification readiness. Rule 7 calls for prompt affected-principal notice and Board intimation without delay, followed by detailed information within 72 hours (subject to Board extension) when in force. |
| §§11–12 access; correction, completion, updating, erasure | Authenticated profile read/update routes exist ([backend/app/api/v1/endpoints/patients.py:156-241](../../backend/app/api/v1/endpoints/patients.py#L156)); these are product profile functions, not a demonstrated rights-request workflow. No backend `/auth/account` deletion endpoint was found even though the client calls one ([frontend/src/shared/services/api.ts:202](../../frontend/src/shared/services/api.ts#L202)). | **P0:** implement verified intake, identity checks, response deadlines, correction/erasure orchestration across primary data, backups, and processors, with legal-retention exceptions and evidence. |
| §13 grievance redressal; Rule 9 contact person | Public help/contact URLs exist in [frontend/src/patient/screens/Settings.tsx:21](../../frontend/src/patient/screens/Settings.tsx#L21), but no Data Protection Officer/responsible privacy contact or grievance service-level process was found. | **P1:** publish the accountable business contact and create a tracked grievance process. |
| §14 nomination | No nomination data model or workflow was found. | **P2:** determine product/legal requirements and implement a verified nomination workflow if applicable. |
| §§9–10 children and Significant Data Fiduciary obligations | No age/parental-consent policy, SDF determination, DPO, data auditor, or periodic DPIA process was found. | **P1:** assess whether children’s data or SDF designation applies; implement required controls if it does. |
| §16 transfers and localization | Deployment service region is Singapore, but database region and transfer destinations are not proven by this repo ([render.yaml:1-28](../../render.yaml#L1), [backend/app/core/config.py:32-36](../../backend/app/core/config.py#L32)). | **P0:** inventory locations and transfers; confirm current government restrictions and any stricter healthcare/contractual requirements. Do not assume Singapore is automatically prohibited by §16. |
| Rules 6–8 processor security, logs, erasure and retention | No log-retention enforcement or processor agreement was found. Rule 6(1)(e) and Rule 8(3) contain one-year retention requirements for the specified security/processing logs and purposes, with other-law exceptions; these rules are scheduled for 13 May 2027. | **P0:** define data-class-specific retention/deletion and ensure the applicable one-year log retention is met when effective; avoid keeping all personal data indefinitely. |
| §§11–14 Data Principal rights and complaint path | No centralized rights-request intake or status tracking was found; patient account profile access and edits alone do not show the full statutory process. | **P0:** create a rights-request workflow covering access, correction, erasure, grievance, and nomination, with identity verification and audit evidence. |

## Known gaps and blockers

- Consent capture and withdrawal are absent.
- Privacy notice/purpose records, a rights-request service, and a privacy/grievance contact are not evidenced.
- A frontend account-deletion call has no matching backend route in the current auth router; confirm and repair before representing erasure as available.
- Region of the managed database and all processors must be verified in provider consoles/contracts. The repo declares Render Singapore services; that alone does not establish the Supabase database region.
- Operational breach-notification capability is not demonstrated. DPDP Rule 7’s timing needs a staffed and rehearsed process before the applicable commencement date.
- Encryption covers selected fields only; cloud storage encryption and key-management evidence are absent.
- Retention/deletion and processor propagation are not automated or evidenced.

## Prioritized actions

1. **P0:** identify legal Data Fiduciary and processing purposes; deploy consent/notice/withdrawal and rights-request flows; confirm residency and processors; build breach response; implement data-class retention and processor agreements.
2. **P1:** publish privacy contact/grievance channel; determine children/SDF scope; add access reviews and documented security-control evidence.
3. **P2:** assess nomination workflow and remaining product-specific obligations.

## Primary references

- [Digital Personal Data Protection Act, 2023 — Ministry of Electronics and Information Technology](https://www.meity.gov.in/static/uploads/2024/02/Digital-Personal-Data-Protection-Act-2023-1.pdf)
- [Digital Personal Data Protection Rules, 2025 — Gazette notification](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf)
- [DPDP Act commencement notification — Gazette of India, 13 November 2025](https://egazette.gov.in/WriteReadData/2025/267647.pdf)
