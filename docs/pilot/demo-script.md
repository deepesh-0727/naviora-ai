# NavioraAI pilot demo script

**Runtime:** 5 minutes, excluding setup and any readiness checks that fail.
**Environment:** production only — `https://naviora-backend-s6je.onrender.com`.
**Audience:** pilot hospital staff and administrators.

> **Readiness note (checked 2026-10-16):** Production `GET /health` and `GET /health/detailed` returned HTTP 200. Detailed health reported database and Redis reachable, but the optional AI dependency was unreachable. The production OpenAPI route returned 404, so production route availability beyond health was not independently confirmed. The repository also shows that voice booking, a text-entry voice fallback, a queue “Complete” button, and a pilot-metrics dashboard widget are not currently wired into the relevant screens. Use the supported live paths below and describe these limitations accurately; do not claim those capabilities during the demo. Recheck readiness immediately before presenting.

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
- Staff can see the test patient in Doctor Queue, and the admin can open Administration and Audit log.
- Any planned SOS test is approved and staffed. Arrange incident cleanup/resolution after the demo.

Verify the public service before opening the apps:

```powershell
curl.exe -i "https://naviora-backend-s6je.onrender.com/health"
curl.exe -i "https://naviora-backend-s6je.onrender.com/health/detailed"
```

Proceed only if both return HTTP 200. In detailed health, confirm `dependencies.database` and `dependencies.redis` are `reachable`. An unavailable optional AI dependency means the voice scene is at risk; use its live manual-booking path and state that voice booking is not available in the current production flow.

**Account roles:** patient, doctor, emergency responder (`emergency`, doctor, nurse, staff, or admin role), and admin/super_admin. Account credentials and production seed data were not available for verification during script preparation; obtain them from the hospital pilot owner through the approved credential process. Do not put passwords or tokens in this document.

## Run of show

The scene allocations below total five minutes. Prep and sign-in happen before the clock starts.

### Scene 1 — Patient appointment booking (80 seconds)

1. On the patient phone, open **Appointments** and choose the booking action. Select a live department, doctor, and available slot; confirm the booking.
2. On the admin laptop, open **Administration** and use **Refresh**. Show the live dashboard data updating. If the dashboard exposes no appointment-specific item, use the Audit log and the patient appointment list to confirm the operation, without claiming a specific KPI changed.
3. Explain the voice limitation plainly: the Voice Assistant accepts recorded audio, but production's intent executor currently executes only emergency intent. A request such as “Book an appointment with Dr. Sharma tomorrow at 2 PM” is not a supported booking operation today. The app has no text-entry fallback. Do not present a manual booking as a successful voice booking.

**If the appointment flow fails:** Retry only once after checking the selected live slot. If no slot/account is available, use the pre-booked demo patient's existing appointment to explain the same live appointment and queue views; label it as an existing appointment, not a booking made during the demo. If neither is available, stop this scene rather than inventing a result.

### Scene 2 — Live queue tracking (50 seconds)

1. On the patient phone, open **Dashboard** and show the test appointment's current queue position.
2. On the staff tablet, open **Doctor Queue**. Use **Move up** on the agreed demo appointment to change its live position. This is the queue operation currently exposed by the screen; it does not mark the previous patient complete.
3. Keep the patient screen visible. Its queue hook listens for the production `queue_update` WebSocket event and reloads appointments; point out the changed position when it updates.

**Fallback:** If the WebSocket update does not arrive promptly, tap **Refresh queue** on the staff screen and refresh the patient Dashboard using the device's normal pull-to-refresh gesture. State that the values are refreshed from production and that live push did not update during this run. Restore the original order if needed.

### Scene 3 — Coordinated emergency response (80 seconds)

> Run this only with the hospital emergency lead's approval and responder ready. This action creates and broadcasts a real production incident.

1. On the demo patient phone, open **Emergency** and press and hold **SOS** for two seconds. Grant location permission if prompted. Confirm the app shows “Emergency signal sent.”
2. On the staff tablet, open **Emergency Console**, select the new incident, and choose **Assign responder** with the approved responder ID. The patient timeline should show the acknowledgment event.
3. In the console, tap **Mark en route**. The patient timeline should show “Help is on the way.” Do not promise an ETA: the current UI does not display or calculate “ETA 3 min.”
4. Resolve or otherwise close the test incident only using the hospital's agreed production procedure after the demo.

**Fallback:** If location permission or SOS submission fails, do not trigger the endpoint repeatedly and do not create an unapproved incident through a direct form/API. If a previously approved production test incident is already active, use that record in the console and clearly say it was pre-created. Otherwise, skip the live response portion and record the demo as blocked; a screenshot is not evidence of a live production response.

### Scene 4 — Admin dashboard and audit log (60 seconds)

1. In the admin panel, open **Administration** and press **Refresh**. The current screen loads the live dashboard KPI, chart, and alert endpoints. Identify the values as the dashboard's available operational data and distinguish empty/unavailable data from zero.
2. Open **Audit log** and inspect recent records. Point to records only when the corresponding action actually appears; do not promise that booking, queue changes, or every SOS action is audited unless the row is present.
3. The separate pilot metrics API is `GET /api/v1/admin/pilot/metrics` and requires an admin login. The current Administration screen does not call this endpoint. Do not describe its contents as displayed in the dashboard unless a deployed UI update has been verified.

**Fallback:** If the dashboard cannot load but production remains reachable, use the live Audit log and the patient/staff records already visible in the apps. If those live views are unavailable too, stop the scene; do not substitute a static screenshot while describing it as live data.

### Closing (30 seconds)

Run or show the pre-checked live response from:

```powershell
curl.exe -i "https://naviora-backend-s6je.onrender.com/health/detailed"
```

Expected at the time of the readiness check: HTTP 200 and JSON with `status: "ok"`, plus dependency fields. Read the current response rather than assuming optional services are healthy. Say that Sentry and UptimeRobot are configured only if the pilot owner has confirmed their current project/monitor status; uptime history comes from UptimeRobot, not the application database.

## Readiness gaps to close before claiming the requested end-to-end demo

- **Voice booking:** not supported by the production intent executor; current voice actions execute emergency only. Voice Assistant also has no text-entry fallback.
- **Doctor Sharma / available slot / test accounts:** not verifiable from repository access. The hospital pilot owner must confirm these against production.
- **Queue completion UI:** Doctor Queue exposes **In room**, **No-show**, and **Move up**; it does not expose the requested “mark previous patient complete” action. The live queue position can still be demonstrated with **Move up** and `queue_update`.
- **SOS wording and ETA:** patient UI says “Emergency signal sent” / “Help is on the way”; no “Staff notified” text or three-minute ETA is implemented in that screen.
- **Admin pilot KPIs:** the dashboard screen fetches `/api/v1/admin/dashboard/kpis`, `/charts`, and `/alerts`, not `/api/v1/admin/pilot/metrics`.
- **Production status:** latest read-only check for this document returned `/health` 200 and `/health/detailed` 200; DB and Redis were reachable, AI was unreachable, SMS/email were not configured. Recheck immediately before the pilot.

If the hospital requires the unimplemented voice booking, appointment-completion UI, exact emergency messages/ETA, or pilot-metrics dashboard for acceptance, treat this as a no-go until those features are deployed and verified in production.
