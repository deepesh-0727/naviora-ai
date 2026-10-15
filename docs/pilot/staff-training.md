# Staff Training Materials

**Audience:** Doctors, nurses, front-desk staff, and emergency responders using the Naviora AI staff app.
**Format:** Instructor-led. Use test accounts and approved test patients only. Never use patient information in training screenshots.
**Estimated time:** 2 hours 45 minutes, including breaks and quizzes.

## Before the session

- Confirm each learner has an active account with the correct role and can sign in.
- Use the hospital-approved test patient and test appointments.
- Confirm the staff app points to the intended environment and the service health check is available.
- Explain that screens and actions depend on role. A doctor, nurse, front-desk worker, and emergency responder will not see identical tabs.
- Do not enter real clinical information in the training environment.

---

## Module 1 — Staff App Basics (30 minutes)

### Learning objectives

By the end of this module, staff can sign in, identify their role-specific tabs, open the relevant queue or work screen, and review notifications.

### Step-by-step

1. Open the staff app and sign in with the account issued to you. Complete any verification step shown by the sign-in flow.
2. Check the role shown by the tabs. Doctors see **Doctor Dashboard**, **Doctor Queue**, **Emergency**, **Notifications**, and **Profile**. Nurses, front-desk staff, pharmacy staff, facilities staff, and emergency responders have their own role-specific tabs.
3. Open **Notifications**. Read the title, message, and timestamp. Tap **Mark as read** where the control is available, then refresh the list to confirm the result.
4. Open **Profile** to review your staff account and current shift/attendance information when available. Use **Staff Settings** only to review configured preferences and signed-in devices.
5. Lock the device according to hospital policy when you finish a shared-device session. A dedicated **Log out** control in the staff tabs is coming in a next release; ask the pilot administrator to reset the session on a shared device.

### Screenshot placeholders

- `[Screenshot: Doctor staff tabs showing Dashboard, Queue, Emergency, Notifications, and Profile.]`
- `[Screenshot: A staff notification with its title, message, timestamp, and Mark as read control.]`

### Common errors and recovery

- **Sign-in is rejected:** Check the account identifier and password, then contact the pilot administrator if the account is inactive. Do not share credentials with another learner.
- **A tab is missing:** Confirm the role assigned to the account. Ask the administrator to correct role access; do not use another person's account.
- **Notifications do not load:** Check connectivity and tap **Refresh notifications**. If the screen reports an unavailable service, record the time and notify the support contact.
- **Session expired:** Sign in again. If repeated, record the displayed error and escalate to support.

### Quiz

1. Why can two staff members see different tabs?
2. What should you do if your account has the wrong role?
3. What should you verify before changing a notification's read status?
4. Is it acceptable to use a colleague's account when yours cannot sign in?
5. What should you do on a shared device after your session?

**Answer key:** 1. Tabs are selected by role. 2. Ask the pilot administrator to correct access. 3. Confirm the notification and action, then verify the result after refresh. 4. No; contact the administrator/support. 5. Lock it according to hospital policy and ask the administrator to reset the session; a dedicated staff Log out control is coming in a next release.

---

## Module 2 — Queue Management (45 minutes)

### Learning objectives

Staff can review the doctor queue, move a patient up when authorized, mark a patient in-room or complete, and record a no-show. Staff can recognize rescheduling and emergency-override gaps.

### Step-by-step

1. A doctor opens **Doctor Queue** and checks the patient ID, queue position, status, and priority before taking action.
2. To change order, tap **Move up** on the approved test appointment. Confirm the update completes and the queue reloads. Do not reorder patients to bypass clinical triage or hospital policy.
3. When the patient enters the room, tap **Mark In-Room**. Confirm the queue refreshes and shows the updated status.
4. When the visit is finished, tap **Mark Complete**. Confirm the success by checking the refreshed queue or appointment record.
5. If a patient has not arrived and the hospital's policy says to record a no-show, tap **No-show**. Verify the resulting status; do not use this action as a substitute for cancellation or rescheduling.
6. If a patient needs a new appointment time, follow the hospital's approved scheduling process. **Staff rescheduling from Doctor Queue is coming in a next release.** Do not alter a queue entry to represent a reschedule.
7. If an emergency requires overriding the ordinary queue, follow the hospital's clinical escalation procedure. **An emergency-override control in Doctor Queue is coming in a next release.**

### Screenshot placeholders

- `[Screenshot: Doctor Queue card with position, status, and the Move up, Mark In-Room, Mark Complete, and No-show controls.]`
- `[Screenshot: Updated queue after a test appointment is marked complete.]`

### Common errors and recovery

- **Queue is empty:** Confirm the doctor account, department, date, and test appointment. Tap **Refresh queue**.
- **Action is still loading:** Wait for the request to finish. Do not tap the action repeatedly.
- **Update fails:** Read the error, confirm connectivity and appointment ID, then retry once. If it fails again, stop and contact support.
- **Wrong patient was changed:** Notify the supervisor immediately and follow the hospital's correction procedure. Do not make a second change to hide the first.
- **WebSocket update does not arrive:** Use **Refresh queue** and verify the current server state. Report that live push did not update.
- **Rescheduling or emergency override is needed:** Use the hospital-approved manual/clinical process and contact the responsible supervisor; the staff app control is not available yet.

### Quiz

1. Which controls mark a visit as started and finished?
2. When is **No-show** appropriate?
3. What should you do if the live queue does not update?
4. Can **Move up** be used to bypass clinical triage?
5. Which staff-app functions are not currently available for this workflow?

**Answer key:** 1. **Mark In-Room** and **Mark Complete**. 2. Only when the patient has not arrived and policy says to record a no-show. 3. Refresh and verify the current state, then report a missing live update. 4. No. 5. Staff rescheduling and a queue emergency-override control; follow hospital procedures meanwhile.

---

## Module 3 — Clinical Actions (60 minutes)

### Learning objectives

Doctors can open the patient record and review its sections, submit a prescription or lab order, and refresh the record. Nurses can review ward tasks and enter vitals using the Nurse Dashboard.

### Step-by-step

1. From **Doctor Queue**, select **View patient** for the approved test appointment. Confirm the patient ID against the test plan before opening the record.
2. In **Patient record**, review **Overview**, **History**, **Vitals**, **Labs**, **Prescriptions**, and **Notes**. Empty sections mean no records are available; do not infer that a test or treatment was performed.
3. To create a prescription, open **Prescriptions** → **Create prescription**. Enter the required appointment ID, medication, dosage, frequency, and duration. Review the fields and submit only an authorized training order for the test patient.
4. To order a lab test, open **Labs** → **Order lab test**. Enter the test name and any relevant optional fields, review, and submit only an authorized test order.
5. Refresh the patient record and verify whether the submitted action appears. If the response says the action is unavailable, do not claim it was saved.
6. A nurse opens **Nurse Dashboard**. Enter the approved ward ID to load ward beds and the medications/vitals due for that ward.
7. For the approved test patient, enter the patient ID and the recorded systolic/diastolic pressure, heart rate, temperature, and oxygen saturation. Add a note if needed, submit the vitals, and verify the success message. Enter observed values only; never invent a reading.

### Screenshot placeholders

- `[Screenshot: Patient record tabs showing Overview, History, Vitals, Labs, Prescriptions, and Notes.]`
- `[Screenshot: Prescription form with required fields, using a test patient and fictional training data.]`
- `[Screenshot: Nurse Dashboard ward selector, due tasks, and vitals-entry form.]`

### Common errors and recovery

- **Patient record is empty or unavailable:** Return to Doctor Queue and open the record from the correct test appointment. Check the patient ID and role access.
- **Prescription or lab action is unavailable:** Stop; the screen may display an endpoint-unavailable message. Follow the hospital's existing clinical process and report the gap.
- **Required field is missing:** Review the form's required fields and correct the test data before submitting.
- **Wrong patient or clinical value entered:** Stop and notify the clinical supervisor immediately. Follow the hospital correction process; do not submit a second record to conceal the first.
- **Nurse tasks do not load:** Confirm the ward ID and network, then refresh. If still unavailable, report the ward ID and time to support.
- **Vitals submission fails:** Do not repeatedly submit. Check the patient ID and units/value format, retry once, and escalate if it fails again.

### Quiz

1. Which screen should a doctor use to see a patient's history and existing orders?
2. What fields are required for a prescription in the patient record form?
3. What should you conclude when a record section says there is no data?
4. Should a nurse estimate a missing vital sign to complete the form?
5. What is the recovery step after entering a value for the wrong patient?

**Answer key:** 1. **Patient record**, opened from the doctor queue. 2. Appointment ID, medication, dosage, frequency, and duration. 3. Only that no record is available in the screen; do not infer that care was performed. 4. No; enter observed values only. 5. Stop, tell the clinical supervisor, and use the hospital's correction procedure.

---

## Module 4 — Emergency Response (30 minutes)

### Learning objectives

Responders can review active incidents, inspect incident details, assign a responder, mark the team en route or arrived, and send a message. Staff can identify the current app limits and use the hospital emergency procedure when necessary.

### Step-by-step

1. Open **Emergency Console** and review the active incident list. Confirm the incident ID, priority, patient, and location before acting.
2. Select **View details** and review available patient details, location, allergies, blood group, and status timeline. Follow hospital privacy policy.
3. Tap **Assign responder**, enter the responder's approved staff ID, and submit. Confirm the updated incident details.
4. When the team begins travel, tap **Mark en route**. When the team reaches the patient, tap **Mark arrived**. Verify each status and timestamp in the timeline.
5. Use **Responder message** to send an appropriate, concise update. Check the conversation for the message after submission.
6. The current console does not expose a separate **Accept** or **Resolve** action. Those controls are **coming in a next release**. Follow the hospital's emergency command and closure procedure, and keep the incident open in the app unless the authorized procedure says otherwise.
7. For a real emergency, use the hospital's emergency response process immediately; the app is a coordination aid and does not replace emergency care or clinical judgment.

### Screenshot placeholders

- `[Screenshot: Emergency Console active incidents with ID, status, priority, and location.]`
- `[Screenshot: Incident details timeline and Assign responder, Mark en route, Mark arrived, and Responder message controls.]`

### Common errors and recovery

- **No incident appears:** Refresh the feed once and verify the correct responder account. If the emergency is real, call the hospital emergency line; do not wait for the app.
- **Location is unclear:** Contact the reporting patient or use the hospital-approved location procedure. Do not guess.
- **Responder assignment fails:** Verify the responder ID and account, then retry once. Escalate through the emergency lead if it still fails.
- **Status or message does not update:** Refresh incident details. Use the hospital's direct communication channel while the app is unavailable.
- **Acknowledge or resolve control is needed:** Follow the established emergency command procedure. The separate app controls are coming in a next release.

### Quiz

1. What should you verify before assigning a responder?
2. Which status should be recorded when the team starts traveling?
3. What should you do if the app is unavailable during a real emergency?
4. Does the current Emergency Console have a separate Accept or Resolve control?
5. Should staff guess a location or ETA that is not shown?

**Answer key:** 1. Incident ID, priority, patient, and location. 2. **Mark en route**. 3. Use the hospital emergency line and established response process immediately. 4. No; those controls are coming in a next release. 5. No; verify information and communicate through approved channels.
