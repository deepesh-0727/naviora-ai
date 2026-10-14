# Security and privacy incident response

**Owner:** Security lead (to be assigned)  
**Review cadence:** At least annually and after an incident or material system change.  
**Status:** Operational roles, contact information, and external notification channels remain to be assigned and exercised.

## First response for every suspected incident

1. **Report immediately** to the designated security lead and on-call engineering lead. If no lead has been assigned, escalate to the engineering manager and organization leadership; assign a temporary incident commander.
2. **Open an incident record** with discovery time, reporter, affected systems, severity, request IDs, decisions, and evidence locations. Do not include credentials or unnecessary patient data in the record.
3. **Contain safely.** Revoke exposed credentials, disable compromised identities, restrict affected network paths, or isolate workloads. Preserve clinical continuity and emergency access with an authorized incident lead.
4. **Preserve evidence.** Capture relevant audit/security logs, deployment/configuration history, provider notices, and forensic snapshots under restricted access. Do not delete affected data or rotate away evidence before a copy is preserved unless immediate containment requires it.
5. **Assess scope and obligations.** Identify systems, data classes, people, locations, processors, access window, and likely impact. Security/privacy leadership and counsel decide contractual, HIPAA, DPDP, and other notifications. Document rationale and deadlines.
6. **Recover and prevent recurrence.** Restore from a verified clean backup where needed, rotate affected secrets, monitor for reuse, validate integrity, and track remediation owners/dates.
7. **Close with a review.** Record timeline, root cause, affected data, notifications, recovery evidence, corrective actions, and policy changes. Re-test controls.

## Scenario playbooks

### API key or application secret exposed

- Revoke/rotate the exposed key at its issuer; rotate related credentials if they shared access.
- If a repository, build log, issue, or chat exposed it, remove public access where possible, but treat the value as compromised even after deletion.
- Review provider access logs and backend audit/deployment logs for use since the earliest possible exposure.
- Invalidate sessions/tokens if signing or encryption material was involved; assess whether encrypted patient fields require key rotation/re-encryption planning.
- Store replacements only in the approved secret manager/deployment environment. Do not paste values into incident tickets or logs.
- Document provider, key scope, revocation time, access review, and remaining exposure.

### Suspected unauthorized database access

- Restrict database network access or disable the compromised account; preserve a snapshot and provider audit logs before destructive cleanup when feasible.
- Rotate database credentials and application secrets; review role grants, public access, exports, snapshots, and processor access.
- Determine tables/records read, changed, copied, or deleted; verify integrity and recovery points.
- Preserve the affected service’s clinical continuity plan; notify the incident lead, privacy/legal contacts, provider, and customer/healthcare organizations according to contract and law.
- Do not assume field encryption makes exposed data harmless; determine which columns were encrypted and whether the key or application runtime was also exposed.

### Patient or other personal data exposed

- Stop the disclosure path, preserve evidence, restrict access, and identify affected people and data categories.
- Coordinate with privacy/legal leadership before notifying individuals; keep a clear record of known facts, uncertainty, and decision deadlines.
- If DPDP applies, Rule 7 (scheduled for 13 May 2027 commencement under the 13 November 2025 staged notification) requires affected Data Principals to be informed without delay and the Board to be informed without delay, with detailed information within 72 hours unless an extension is allowed. Confirm then-current law and any later notification before acting.
- If HIPAA applies, counsel/privacy leadership must assess the Breach Notification Rule and required notices; the software repository does not determine applicability or reportability.
- Give affected people a clear contact channel and safety steps. Keep copies of notices and delivery evidence.

### DDoS or service-availability attack

- Declare an availability incident and coordinate with hosting, DNS, CDN/WAF, and network providers. Preserve logs and attack indicators.
- Apply provider-level filtering/rate controls and protect authentication, clinical, and emergency workflows. Do not block emergency workflows without an approved continuity decision.
- Monitor database/Redis saturation, queue buildup, and recovery behavior; scale or shed noncritical work using the incident commander’s decision.
- Restore normal routing gradually, verify readiness and data integrity, and document service impact and provider actions.

## Required operational contacts (fill before production)

- Incident commander / security lead: **unassigned — P0**
- Privacy lead / Data Protection Officer if applicable: **unassigned — P0**
- Engineering on-call: **unassigned — P0**
- Hosting, database, Redis, SMS/email, and monitoring provider escalation details: **unassigned — P1**
- Customer/covered-entity and regulator notification owners: **unassigned — P0**

## Exercise and evidence

Run a tabletop exercise at least annually, and before production processing of sensitive health data. Exercise credential exposure, unauthorized database access, personal-data breach, and DDoS scenarios. Keep attendance, timeline, decisions, evidence-retention location, findings, owners, and retest results. A written playbook is not evidence that the response has been exercised.

## References

- [HHS — HIPAA Security Rule incident and contingency safeguards](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html)
- [DPDP Rules, 2025 — Rules 6 and 7](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf)
- [DPDP Act commencement notification — Gazette of India](https://egazette.gov.in/WriteReadData/2025/267647.pdf)
