# NavioraAI pilot demo script

**Runtime:** 5 minutes, excluding setup and any readiness checks that fail.
**Environment:** production only — `https://naviora-backend-s6je.onrender.com`.
**Audience:** pilot hospital staff and administrators.

> **Readiness note (checked 2026-10-16):** Production `GET /health` and `GET /health/detailed` returned HTTP 200. Detailed health reported database and Redis reachable, while the optional AI dependency was unreachable. Voice booking now uses rule-based intent fallback when the LLM is unreachable, and the voice response reports `fallback_used`; booking still requires an explicit yes/no confirmation. The repository includes the voice recording/upload screen, queue completion controls, and Pilot Metrics screen. The latest frontend build's availability on the pilot device and physical microphone behavior were not verified; install and check the intended app build before the demo. Recheck readiness immediately before presenting.

## Prep (before the 5-minute clock)

Have these ready:

- Patient app signed in on a phone as a **patient** account.
- Staff app signed in on a tablet as a **doctor** account assigned to the same department and queue; have a separate **emergency responder** account available if it is not the same staff user.
- Admin panel signed in on a laptop as an **admin** or **super_admin** account.
- Stable internet, working microphone and location permission on the phone, and the phone/tablet/laptop on the same demo network if required by the WebSocket setup.
- An agreed, clearly identified pilot demo patient and a coordinated responder. Do not use a real patient's data.
- A non-urgent, authorized production test incident plan approved by the hospital's emergency lead. SOS creates a real production emergency record and broadcasts to the response team; never trigger it as a surprise or during a real emergency.

Ask the hospital administrator to confirm in production before the meeting that:

- The patient, doctor, responder, and admin test accounts exist and can sign in.
- The patient account is linked to a patient profile and has an appointment in an active queue; its queue position is greater than zero.
- Keep that queue appointment separate from the new appointment booked in Scene 1 unless the hospital has already arranged the production check-in step between scenes.
- The doctor and department used for the booking exist, are active, and have a slot available. Do not assume “Dr. Sharma” exists; verify the displayed doctor and slot in the live booking flow.
- Staff can see the agreed test appointment in Doctor Queue, and the admin can open Pilot Metrics and Audit Log.
- The patient app build includes the current Voice Assistant recording flow. Confirm microphone permission on the demo phone before starting.
- Any planned SOS test is approved and staffed. Arrange incident cleanup/resolution after the demo.

Verify the public service before opening the apps:

```powershell
curl.exe -i "https://naviora-backend-s6je.onrender.com/health"
curl.exe -i "https://naviora-backend-s6je.onrender.com/health/detailed"
```

Proceed only if both return HTTP 200. In detailed health, confirm `dependencies.database` and `dependencies.redis` are `reachable`. If the optional AI dependency is unreachable, rule-based voice classification remains available; verify the response displays the **Rule mode** badge. If recording or transcription fails, move to the regular Appointments screen and label that as the manual fallback.

**Account roles:** patient, doctor, emergency responder (`emergency`, doctor, nurse, staff, or admin role), and admin/super_admin. Account credentials and production seed data were not available for verification during script preparation; obtain them from the hospital pilot owner through the approved credential process. Do not put passwords or tokens in this document.

## Run of show

The scene allocations below total five minutes. Prep and sign-in happen before the clock starts.

### Scene 1 — Patient voice appointment booking (80 seconds)

1. On the patient phone, open **Voice Assistant**, press and hold the microphone, and say: “Book an appointment with Dr. [verified doctor name] on [verified date] at [available time].” Release the button to upload the recording.
2. Show the transcript and response. If the response has a **Rule mode** badge, explain that the system used its rule-based classifier because the LLM was unavailable.
3. When the assistant asks “Confirm booking? Say yes to confirm or no to cancel,” say “yes.” Show the confirmation response and the new appointment in the patient’s Appointments list. The first utterance prepares a proposal; the appointment is written only after confirmation.
4. If the mic or transcription path fails, open **Appointments** and book manually. Call this the manual fallback, not a voice booking.

**If the appointment flow fails:** Retry only once after checking the account, doctor, and live slot. If no slot/account is available, use the pre-booked demo patient's existing appointment to explain the appointment view; label it as existing data, not a booking made during the demo. If neither is available, stop this scene rather than inventing a result.

### Scene 2 — Live queue tracking (50 seconds)

1. On the patient phone, open **Dashboard** and show the test appointment's current queue position.
2. On the staff tablet, open **Doctor Queue** and tap **Mark Complete** for the agreed previous patient. Confirm the status update succeeds and the queue refreshes.
3. Keep the patient screen visible. The queue view listens for the production `queue_update` WebSocket event and reloads appointments; point out the position change when it updates.

**Fallback:** If the WebSocket update does not arrive promptly, tap **Refresh queue** on the staff screen and refresh the patient Dashboard using its pull-to-refresh gesture. State that live push did not update during this run. Restore the original queue state if needed.

### Scene 3 — Coordinated emergency response (80 seconds)

> Run this only with the hospital emergency lead's approval and responder ready. This action creates and broadcasts a real production incident.

1. On the demo patient phone, open **Emergency** and press and hold **SOS** for two seconds. Grant location permission if prompted. Confirm the app shows “Emergency signal sent.”
2. On the staff tablet, open **Emergency Console**, select the new incident, and choose **Assign responder** with the approved responder ID. The patient timeline should show the acknowledgment event.
3. In the console, tap **Mark en route**. The patient timeline should show “Help is on the way.” Do not promise an ETA: the current UI does not display or calculate “ETA 3 min.”
4. Resolve or otherwise close the test incident only using the hospital's agreed production procedure after the demo.

**Fallback:** If location permission or SOS submission fails, do not trigger the endpoint repeatedly and do not create an unapproved incident through a direct form/API. If a previously approved production test incident is already active, use that record in the console and clearly say it was pre-created. Otherwise, skip the live response portion and record the demo as blocked; a screenshot is not evidence of a live production response.

### Scene 4 — Admin pilot metrics and audit log (60 seconds)

1. In the admin panel, open **Pilot Metrics**. Show the wait time, emergency response, no-show, voice, staff, and uptime cards. Use pull-to-refresh if needed; automatic refresh runs every 60 seconds. Empty samples correctly read **No data yet**, not zero.
2. Open **Audit Log** and inspect recent records. Point to records only when the corresponding action actually appears; do not promise that every action is audited unless its row is present.

**Fallback:** If Pilot Metrics cannot load but production remains reachable, use the live Audit Log and patient/staff records already visible in the apps. If those live views are unavailable too, stop the scene; do not substitute a static screenshot while describing it as live data.

### Closing (30 seconds)

Run or show the pre-checked live response from:

```powershell
curl.exe -i "https://naviora-backend-s6je.onrender.com/health/detailed"
```

Expected at the time of the readiness check: HTTP 200 and JSON with `status: "ok"`, plus dependency fields. Read the current response rather than assuming optional services are healthy. Say that Sentry and UptimeRobot are configured only if the pilot owner has confirmed their current project/monitor status; uptime history comes from UptimeRobot, not the application database.

## Readiness checks before presenting the end-to-end demo

- **Voice booking:** the backend and app flow are implemented. First utterance creates a pending proposal; explicit confirmation creates the appointment. An LLM-unavailable response uses rule mode. The physical-device microphone path and installed app build still need a pre-demo check.
- **Doctor Sharma / available slot / test accounts:** not verifiable from repository access. The hospital pilot owner must confirm these against production.
- **Queue completion UI:** Doctor Queue exposes **Mark In-Room**, **Mark Complete**, **No-show**, and **Move up**. Confirm the staff account can update the selected production appointment.
- **SOS wording and ETA:** patient UI says “Emergency signal sent” / “Help is on the way”; no “Staff notified” text or three-minute ETA is implemented in that screen.
- **Admin pilot metrics:** the **Pilot Metrics** screen calls `GET /api/v1/admin/pilot/metrics`. Some values remain empty until real pilot events or reviews are recorded; uptime is sourced externally from UptimeRobot.
- **Production status:** latest read-only check for this document returned `/health` 200 and `/health/detailed` 200; DB and Redis were reachable, AI was unreachable, SMS/email were not configured. Recheck immediately before the pilot.

If the hospital requires exact emergency messages or a three-minute ETA for acceptance, treat this as a no-go until those behaviors are implemented and verified. Also confirm the latest mobile app build is installed and the production test accounts, doctor, slot, and approved demo incident are ready before presenting.
