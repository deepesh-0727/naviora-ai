# Pilot Support Runbook

Use this runbook with the hospital's approved incident and patient-safety procedures. Record the incident time, affected workflow, environment, app version, steps already tried, and outcome. Do not put patient-identifying details in an unapproved support channel. For immediate patient danger, use the hospital's emergency phone process first.

## Triage and escalation

| Issue | First response | Escalation |
|---|---|---|
| Backend unavailable | Check `/health` and `/health/detailed`, then inspect the Render service and recent deploy logs. Keep manual workflows active. | Notify Provider on-call; notify hospital IT if unavailable for more than 5 minutes or sooner if safety workflows are affected. |
| Patient cannot log in | Confirm the patient is using the registered phone number, has network access, and requested a fresh OTP. | Follow the hospital's identity verification process and escalate repeated OTP delivery failures to Provider support; never share an OTP. |
| Voice booking broken | Check microphone permission, connection, and whether the app shows an error or Rule mode. Offer the app's available touch booking or the hospital's normal booking route. | Escalate repeated transcription/classification failures with app version and a non-identifying example; do not record or send patient speech without approved consent. |
| Appointment missing | Confirm the patient checked the correct account/date and that the booking was explicitly confirmed. Check the appointment in the authorized staff view/database tools. | If no appointment exists, use the hospital's authorized manual booking process and notify Provider support with the appointment/request reference. |
| SOS not received | Call the hospital emergency line/team immediately and follow hospital emergency procedure; do not wait for app troubleshooting. | Notify hospital incident lead and Provider on-call after immediate response is underway. Record the time and delivery evidence without delaying care. |
| Queue does not update | Check network and connection status; reload the patient view if available and have staff confirm the current queue in their staff screen. | Use the staff-confirmed/manual queue process and escalate repeated sync/WebSocket failures to Provider support. |
| Push notification missing | Check device notification permission, network, and whether the event is visible in the app. | Use an approved direct contact method for time-sensitive communication; escalate persistent delivery failures. |
| Feedback cannot submit | Check network, required fields, completed appointment eligibility, and whether feedback was already submitted. | Capture the HTTP/status message without patient details and escalate if the authorized retry fails. |

## 1. Backend down

**Symptom:** App requests fail, the health check does not return successfully, or users report a broad outage.

**Diagnostic:** From an approved workstation, request `https://naviora-backend-s6je.onrender.com/health` and `/health/detailed`. Check the Render service status, latest deploy, and logs for the matching time window. Determine whether the issue affects all users or one network/device.

**Resolution:** Keep the hospital's normal appointment, queue, and emergency processes active. Provider on-call investigates the service and coordinates a restart or rollback only through the approved deployment process. Do not restart production services from an unapproved account.

**Contact / target:** Provider on-call **[name/phone TBD]**; hospital IT **[contact TBD]**. Acknowledge immediately; notify hospital IT if outage exceeds 5 minutes or sooner for safety impact. Target restoration is incident-specific; do not promise a fixed recovery time.

## 2. Patient cannot log in

**Symptom:** OTP does not arrive, is rejected, or registration cannot complete.

**Diagnostic:** Confirm the entered mobile number with the patient, check cellular/SMS coverage and device time, and ask whether a recent OTP was used. Do not ask the patient to disclose the OTP to support staff.

**Resolution:** Have the patient request a new OTP and use the latest code. If identity or account details need correction, follow the hospital's identity verification process. The app's staff surfaces do not establish a safe manual reset workflow; use an authorized account-administration process only.

**Contact / target:** Hospital registration desk **[contact TBD]**, then Provider support **[contact TBD]** for repeated delivery or application errors. Target: resolve during the visit where possible; otherwise keep the hospital's normal registration process available.

## 3. Voice broken

**Symptom:** Recording cannot start, transcription fails, or a booking proposal is wrong or unclear.

**Diagnostic:** Check microphone permission and network. Note whether an error is displayed and whether the response indicates Rule mode. Ask the patient to review the words and appointment details shown; never treat an unconfirmed proposal as a booking.

**Resolution:** Offer touch-based booking or the hospital's normal booking route. If a proposal is incorrect, do not confirm it; start a corrected request. Retry only with the patient's consent.

**Contact / target:** Reception for booking assistance; Provider support **[contact TBD]** for repeated app errors. Target: provide another booking route immediately; technical fix timing depends on diagnosis.

## 4. Appointment missing

**Symptom:** Patient expects an appointment but cannot see it, or staff cannot find it.

**Diagnostic:** Verify the patient account and requested date/time. Confirm whether the voice or booking flow reached its explicit confirmation step. An unconfirmed proposal is not a saved appointment. Check the authorized staff record using the hospital's approved access process.

**Resolution:** If no record exists, authorized hospital staff may create the appointment through the normal scheduling workflow. Confirm the appointment with the patient and reconcile any duplicate before retrying a booking.

**Contact / target:** Reception/scheduling lead **[contact TBD]**; Provider support **[contact TBD]** if a confirmed booking is absent. Target: resolve before the patient leaves when feasible.

## 5. SOS not received

**Symptom:** Patient does not receive a visible acknowledgement or the emergency team cannot see the alert.

**Diagnostic:** **Do not delay urgent care to diagnose the app.** Call the hospital emergency line or alert nearby staff immediately. Once care is underway, record the approximate time, device/network, and app acknowledgement shown.

**Resolution:** Follow hospital emergency procedures and communicate directly with the response team. Treat the app as an additional alert channel, not the sole emergency channel. Preserve relevant logs through the approved incident process.

**Contact / target:** Hospital emergency line/team **[number/contact required before pilot]**, then hospital incident lead and Provider on-call **[contact TBD]**. Immediate human response takes priority; target acknowledgement for technical escalation is immediate after the emergency call.

## 6. Queue does not update

**Symptom:** Patient position appears stale or staff action is not reflected on patient screen.

**Diagnostic:** Ask staff to confirm the current queue in the Doctor Queue/staff screen. Check device connectivity and whether the app can reload. Compare the appointment status and timestamp through an authorized staff view.

**Resolution:** Staff should communicate the confirmed queue position directly and continue the hospital's normal queue process. Patient can reload the screen if needed. Do not ask staff to mark an appointment complete unless the visit is actually complete.

**Contact / target:** Department super-user **[contact TBD]**, then Provider support **[contact TBD]** for repeated synchronization failure. Target: communicate the correct position during the visit.

## 7. Push or feedback problem

**Symptom:** A notification does not appear, or the feedback form cannot be submitted.

**Diagnostic:** Check notification permission, network, completed-appointment eligibility, required fields, and whether feedback was already submitted. Record the visible error and time without copying patient data.

**Resolution:** Use an approved direct communication method for important information. Feedback can be retried after connectivity returns if it has not already been submitted. Do not create duplicate feedback or infer an NPS score from a star rating.

**Contact / target:** Hospital super-user and Provider support **[contacts TBD]**. Target: follow up through the approved channel; no patient-care action should depend on feedback delivery.

## Incident record

- Incident reference: ____________________
- Reported at / by: ______________________
- Affected workflow and app version: ______
- Immediate workaround used: _____________
- Escalated to / time: ____________________
- Resolution / follow-up owner: ___________

Before pilot start, fill in every **[contact TBD]** field, test the emergency phone route, and review this runbook with hospital IT, the clinical/safety owner, and Provider on-call.
