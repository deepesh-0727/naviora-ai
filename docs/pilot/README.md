# Pilot Preparation Index

This index tracks the pilot preparation materials committed in this repository. “Ready” means the document or code deliverable is present; it does not mean the hospital has approved it, production prerequisites are configured, or the workflow has passed a live hospital acceptance test.

## Phase 11 deliverables

| Batch | Deliverable | Status | Follow-up / constraint |
|---|---|---|---|
| 1 | [Success metrics](success-metrics.md) | Complete | Uptime is sourced externally; voice accuracy needs reviewed interactions and must show sample size. |
| 1b | Persisted voice interactions and NPS schema | Complete | Migration chain includes voice interactions and `feedback.nps_score`; verify production migration on deploy. |
| 2 | Pilot Metrics API and admin dashboard | Complete | Empty samples are reported as no data; external uptime remains separately sourced. |
| 3 | [Five-minute demo script](demo-script.md) | Draft ready | Verify production accounts, app build, seeded clinicians, physical device audio, and live scenes before presenting. |
| 4 | [Staff training](staff-training.md) | Draft ready | Review role-specific material with the hospital; noted unavailable controls are future work. |
| 5 | [Patient onboarding flier](patient-onboarding.md) | Draft ready | Play Store URL/QR, support phone, approved privacy wording, and Hindi translation are still required. |
| 6 | [Pilot agreement](pilot-agreement.md) | Discussion template | Not legally binding. Hospital/Provider legal review, legal entity details, final data terms, liability, and signatures are required. |
| 7 | [Installation checklist](installation-checklist.md) | Ready for site-specific completion | Hospital Wi-Fi, devices, integration, contacts, acceptance tests, baselines, and written go-live approvals remain site work. |
| 8 | Feedback survey, reminder and NPS card | Complete; Test and Deploy green for `bbc87be` | Actual push delivery requires Firebase credentials and patient device registration. The survey asks a separate 0–10 NPS question so the metric is not inferred from stars. |
| 9 | [Support runbook](support-runbook.md) | Draft ready | Fill in every contact/phone placeholder and rehearse escalation and emergency phone fallback. |

## Before a hospital pilot

- Confirm the hospital, departments, named pilot lead, clinical/safety owner, IT/security contact, super-users, and emergency response route.
- Have counsel review the final pilot agreement, data-processing terms, privacy notice, and applicable legal obligations.
- Complete production device/build testing, test account setup, Play Store distribution details, push registration, database migration verification, and end-to-end acceptance checks.
- Add the verified flier QR, support number, reviewed Hindi translation, and approved privacy wording.
- Record baseline metrics and measurement owners before collecting pilot results.
- Test an end-to-end reminder with a designated test patient and active registered device; CI does not verify production Firebase delivery.

## Owner-only roadmap actions

The business and operational activities in Track E and the final human walkthrough remain with the project owner: Render plan/domain decisions, SSL Labs verification, LinkedIn and outreach, Calendly, hospital target list/contact, tablet purchase/printing, legal review, final README refresh, and human review/sign-off of all pilot and Phase 12 documents. This repository cannot verify or perform those account, purchasing, legal, or outreach actions.
