# API Reference

This inventory is generated from the FastAPI routes and OpenAPI schema in the repository. Rebuild/verify it from `backend/app/main.py` and route modules whenever endpoints change. The canonical machine-readable contract is `GET /api/v1/openapi.json`; interactive docs are `/docs`.

## Authentication and access

- API routes require `Authorization: Bearer <access_token>` unless listed in `PUBLIC_API_PATHS` / `PUBLIC_API_PREFIXES` in `backend/app/main.py`.
- `/api/v1/admin/**` additionally requires the `admin` or `super_admin` role; `/api/v1/staff/**` requires a staff or admin role. Individual routes may apply narrower role checks.
- Public routes currently include auth registration/login/OTP/refresh/password recovery, department discovery, navigation department discovery, and `/api/v1/health`.
- `/metrics` is separately protected by the `X-Metrics-Token` policy / configured network allowlist. Health and root routes are public operational endpoints.
- `POST /api/v1/feedback` requires a signed-in patient and only accepts feedback for that patient’s completed appointment. `nps_score` is optional at the API layer and must be 0–10 when supplied.

## Endpoints

| Method | Path | Purpose | Auth | Request | Success response |
|---|---|---|---|---|---|
| `GET` | `/` | Root | Public / separately guarded | — | 200 (application/json: —) |
| `HEAD` | `/` | Root Head | Public / separately guarded | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/analytics/doctor-productivity` | Doctor Productivity | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/analytics/emergency` | Emergency Analytics | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/analytics/export` | Export Analytics | Bearer; admin | —query: dataset | 200 (application/json: —) |
| `GET` | `/api/v1/admin/analytics/flow` | Appointment Flow | Bearer; admin | —query: days | 200 (application/json: —) |
| `GET` | `/api/v1/admin/analytics/no-shows` | No Shows | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/analytics/voice` | Voice Analytics | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/analytics/wait-times` | Wait Times | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/audit` | List Audit Logs | Bearer; admin | —query: limit, offset | 200 (application/json: —) |
| `GET` | `/api/v1/admin/audit/export/csv` | Export Audit Logs | Bearer; admin | —query: limit | 200 (application/json: —) |
| `GET` | `/api/v1/admin/audit/{audit_id}` | Audit Log Detail | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/billing/bills` | List Bills | Bearer; admin | —query: limit, offset | 200 (application/json: —) |
| `GET` | `/api/v1/admin/billing/invoices` | List Invoices | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/billing/payments` | List Payments | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/billing/refunds` | List Refunds | Bearer; admin | — | 200 (application/json: —) |
| `POST` | `/api/v1/admin/billing/refunds` | Request Refund | Bearer; admin | application/json: RefundRequest | 201 (application/json: —) |
| `GET` | `/api/v1/admin/billing/revenue` | Revenue Summary | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/dashboard/alerts` | Dashboard Alerts | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/dashboard/charts` | Dashboard Charts | Bearer; admin | —query: days | 200 (application/json: —) |
| `GET` | `/api/v1/admin/dashboard/kpis` | Dashboard Kpis | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/departments` | List Departments | Bearer; admin | — | 200 (application/json: —) |
| `POST` | `/api/v1/admin/departments` | Create Department | Bearer; admin | application/json: DepartmentCreate | 201 (application/json: —) |
| `DELETE` | `/api/v1/admin/departments/{department_id}` | Delete Department | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/departments/{department_id}` | Get Department | Bearer; admin | — | 200 (application/json: —) |
| `PUT` | `/api/v1/admin/departments/{department_id}` | Update Department | Bearer; admin | application/json: DepartmentUpdate | 200 (application/json: —) |
| `GET` | `/api/v1/admin/departments/{department_id}/doctors` | Department Doctors | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/departments/{department_id}/waypoints` | Department Waypoints | Bearer; admin | — | 200 (application/json: —) |
| `POST` | `/api/v1/admin/departments/{department_id}/waypoints` | Create Waypoint | Bearer; admin | application/json: WaypointCreate | 201 (application/json: —) |
| `POST` | `/api/v1/admin/health/cache/clear` | Clear Application Cache | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/health/errors` | Recent Errors | Bearer; admin | —query: limit | 200 (application/json: —) |
| `GET` | `/api/v1/admin/health/latency` | Service Latency | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/health/services` | Service Health | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/pilot/metrics` | Get Pilot Metrics | Bearer; admin | —query: start, end | 200 (application/json: —) |
| `GET` | `/api/v1/admin/resources/beds` | List Beds | Bearer; admin | — | 200 (application/json: —) |
| `PUT` | `/api/v1/admin/resources/beds/{bed_id}` | Update Bed | Bearer; admin | application/json: ResourceStatus | 200 (application/json: —) |
| `GET` | `/api/v1/admin/resources/equipment` | List Equipment | Bearer; admin | — | 200 (application/json: —) |
| `POST` | `/api/v1/admin/resources/equipment` | Create Equipment | Bearer; admin | application/json: EquipmentCreate | 201 (application/json: —) |
| `PUT` | `/api/v1/admin/resources/equipment/{equipment_id}` | Update Equipment | Bearer; admin | application/json: EquipmentUpdate | 200 (application/json: —) |
| `GET` | `/api/v1/admin/resources/ors` | List Operating Rooms | Bearer; admin | — | 200 (application/json: —) |
| `POST` | `/api/v1/admin/resources/ors/block` | Block Operating Room | Bearer; admin | application/json: RoomBlock | 200 (application/json: —) |
| `PUT` | `/api/v1/admin/resources/ors/{room_id}` | Update Operating Room | Bearer; admin | application/json: ResourceStatus | 200 (application/json: —) |
| `GET` | `/api/v1/admin/settings` | List Settings | Bearer; admin | — | 200 (application/json: —) |
| `PUT` | `/api/v1/admin/settings` | Update Setting | Bearer; admin | application/json: SettingUpdate | 200 (application/json: —) |
| `POST` | `/api/v1/admin/settings/test-integration` | Test Integration | Bearer; admin | application/json: IntegrationTest | 200 (application/json: —) |
| `GET` | `/api/v1/admin/users` | List Users | Bearer; admin | —query: role | 200 (application/json: —) |
| `POST` | `/api/v1/admin/users` | Create User | Bearer; admin | application/json: UserCreate | 201 (application/json: —) |
| `DELETE` | `/api/v1/admin/users/devices/{device_id}` | Delete User Device | Bearer; admin | — | 200 (application/json: —) |
| `DELETE` | `/api/v1/admin/users/{user_id}` | Deactivate User | Bearer; admin | — | 200 (application/json: —) |
| `GET` | `/api/v1/admin/users/{user_id}` | Get User | Bearer; admin | — | 200 (application/json: —) |
| `PUT` | `/api/v1/admin/users/{user_id}` | Update User | Bearer; admin | application/json: UserUpdate | 200 (application/json: —) |
| `GET` | `/api/v1/admin/users/{user_id}/devices` | List User Devices | Bearer; admin | — | 200 (application/json: —) |
| `POST` | `/api/v1/admin/users/{user_id}/reset-password` | Reset Password | Bearer; admin | application/json: PasswordReset | 200 (application/json: —) |
| `GET` | `/api/v1/analytics/audit-logs` | Get System Audit Logs | Bearer (route may restrict role) | —query: limit | 200 (application/json: —) |
| `GET` | `/api/v1/analytics/kpis` | Get Hospital Kpis | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `GET` | `/api/v1/analytics/reports` | Get Operational Reports | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `GET` | `/api/v1/appointments` | List Appointments | Bearer (route may restrict role) | —query: upcoming | 200 (application/json: array of AppointmentResponse) |
| `POST` | `/api/v1/appointments` | Book Appointment | Bearer (route may restrict role) | application/json: app__api__v1__endpoints__appointments__AppointmentCreate | 201 (application/json: AppointmentResponse) |
| `GET` | `/api/v1/appointments/` | List Appointments | Bearer (route may restrict role) | —query: upcoming | 200 (application/json: array of AppointmentResponse) |
| `GET` | `/api/v1/appointments/doctor/{doctor_id}/availability` | Get Doctor Availability | Bearer (route may restrict role) | —query: date | 200 (application/json: —) |
| `GET` | `/api/v1/appointments/queue` | Get Queue Status | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `DELETE` | `/api/v1/appointments/{id}` | Cancel Appointment | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `GET` | `/api/v1/appointments/{id}` | Get Appointment | Bearer (route may restrict role) | — | 200 (application/json: AppointmentResponse) |
| `PUT` | `/api/v1/appointments/{id}` | Update Appointment | Bearer (route may restrict role) | application/json: AppointmentUpdate | 200 (application/json: —) |
| `POST` | `/api/v1/auth/forgot-password` | Forgot Password | Public / separately guarded | —query: email | 200 (application/json: —) |
| `POST` | `/api/v1/auth/login` | Login | Public / separately guarded | application/x-www-form-urlencoded: Body_login_api_v1_auth_login_post | 200 (application/json: Token) |
| `POST` | `/api/v1/auth/logout` | Logout | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `GET` | `/api/v1/auth/me` | Current User | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `PUT` | `/api/v1/auth/me` | Update Current User | Bearer (route may restrict role) | application/json: UserProfileUpdate | 200 (application/json: —) |
| `POST` | `/api/v1/auth/otp/generate` | Generate Otp | Public / separately guarded | —query: phone | 200 (application/json: —) |
| `POST` | `/api/v1/auth/otp/verify` | Verify Otp | Public / separately guarded | application/json: OTPVerification | 200 (application/json: —) |
| `POST` | `/api/v1/auth/refresh` | Refresh Token | Public / separately guarded | —query: refresh_token | 200 (application/json: Token) |
| `POST` | `/api/v1/auth/register` | Register | Public / separately guarded | application/json: UserRegister | 201 (application/json: —) |
| `POST` | `/api/v1/auth/reset-password` | Reset Password | Public / separately guarded | application/json: ResetPasswordRequest | 200 (application/json: —) |
| `POST` | `/api/v1/billing/create-razorpay-order` | Create Razorpay Order | Bearer (route may restrict role) | application/json: CreateRazorpayOrderRequest | 200 (application/json: —) |
| `POST` | `/api/v1/billing/estimate` | Get Bill Estimate | Bearer (route may restrict role) | application/json: — | 200 (application/json: BillingEstimate) |
| `GET` | `/api/v1/billing/history` | Get Billing History | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `GET` | `/api/v1/billing/invoices` | List Invoices | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `POST` | `/api/v1/billing/invoices` | Create Invoice | Bearer (route may restrict role) | application/json: app__schemas__billing__BillingCreate | 200 (application/json: Billing) |
| `PATCH` | `/api/v1/billing/invoices/{billing_id}/pay` | Pay Invoice | Bearer (route may restrict role) | —query: payment_method, transaction_id | 200 (application/json: Billing) |
| `GET` | `/api/v1/billing/invoices/{id}` | Get Invoice Details | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `POST` | `/api/v1/billing/payment` | Make Payment | Bearer (route may restrict role) | application/json: PaymentRequest | 200 (application/json: —) |
| `GET` | `/api/v1/departments` | List Departments | Public / separately guarded | — | 200 (application/json: array of object) |
| `GET` | `/api/v1/departments/` | List Departments | Public / separately guarded | — | 200 (application/json: array of object) |
| `GET` | `/api/v1/departments/{department_id}` | Get Department | Public / separately guarded | — | 200 (application/json: object) |
| `GET` | `/api/v1/doctors` | List Doctors | Bearer (route may restrict role) | — | 200 (application/json: array of Doctor) |
| `GET` | `/api/v1/doctors/` | List Doctors | Bearer (route may restrict role) | — | 200 (application/json: array of Doctor) |
| `PUT` | `/api/v1/doctors/availability` | Update Availability | Bearer (route may restrict role) | —query: id, available | 200 (application/json: —) |
| `GET` | `/api/v1/doctors/available` | Get Available Doctors | Bearer (route may restrict role) | — | 200 (application/json: array of Doctor) |
| `GET` | `/api/v1/doctors/department/{department_id}` | Get Doctors By Dept | Bearer (route may restrict role) | — | 200 (application/json: array of Doctor) |
| `GET` | `/api/v1/doctors/patients/{patient_id}/notes` | Get Patient Notes | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `POST` | `/api/v1/doctors/patients/{patient_id}/notes` | Save Patient Note | Bearer (route may restrict role) | application/json: PatientNoteCreate | 200 (application/json: —) |
| `GET` | `/api/v1/doctors/profile` | Get Current Doctor Profile | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `PUT` | `/api/v1/doctors/profile` | Update Current Doctor Profile | Bearer (route may restrict role) | application/json: DoctorProfileUpdate | 200 (application/json: —) |
| `GET` | `/api/v1/doctors/schedule` | Get Doctor Schedule | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `POST` | `/api/v1/doctors/schedule` | Create Doctor Schedule | Bearer (route may restrict role) | application/json: ScheduleCreate | 201 (application/json: —) |
| `GET` | `/api/v1/doctors/{id}` | Get Doctor | Bearer (route may restrict role) | — | 200 (application/json: Doctor) |
| `GET` | `/api/v1/doctors/{id}/availability` | Get Doctor Availability By Date | Bearer (route may restrict role) | —query: date | 200 (application/json: —) |
| `GET` | `/api/v1/emergency/active` | Get Active Emergencies | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `GET` | `/api/v1/emergency/nearby-staff` | Get Nearby Staff | Bearer (route may restrict role) | —query: latitude, longitude | 200 (application/json: —) |
| `PUT` | `/api/v1/emergency/resolve/{id}` | Resolve Emergency | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `POST` | `/api/v1/emergency/respond/{emergency_id}` | Respond To Emergency | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `POST` | `/api/v1/emergency/sos` | Trigger Sos | Bearer (route may restrict role) | application/json: SOSRequest | 200 (application/json: —) |
| `POST` | `/api/v1/emergency/staff-acknowledge` | Acknowledge Emergency | Bearer (route may restrict role) | —query: emergency_id | 200 (application/json: —) |
| `PUT` | `/api/v1/emergency/staff-arrived` | Staff Arrived | Bearer (route may restrict role) | —query: emergency_id | 200 (application/json: —) |
| `GET` | `/api/v1/emergency/status/{id}` | Get Emergency Status | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `POST` | `/api/v1/emergency/trigger` | Trigger Sos | Bearer (route may restrict role) | application/json: SOSRequest | 200 (application/json: —) |
| `POST` | `/api/v1/feedback` | Create Feedback | Bearer (route may restrict role) | application/json: FeedbackCreate | 201 (application/json: FeedbackResponse) |
| `GET` | `/api/v1/location/staff/nearby` | Get Nearby Staff | Bearer (route may restrict role) | —query: building, floor | 200 (application/json: —) |
| `POST` | `/api/v1/location/update` | Update Location | Bearer (route may restrict role) | application/json: LocationUpdate | 200 (application/json: Location) |
| `GET` | `/api/v1/navigation/departments` | List Departments | Public / separately guarded | — | 200 (application/json: array of object) |
| `GET` | `/api/v1/navigation/departments/{id}` | Get Department | Public / separately guarded | — | 200 (application/json: object) |
| `GET` | `/api/v1/navigation/floor-map` | Get Floor Map | Bearer (route may restrict role) | —query: floor | 200 (application/json: —) |
| `GET` | `/api/v1/navigation/poi` | Get Points Of Interest | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `GET` | `/api/v1/navigation/route` | Get Navigation Route | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `POST` | `/api/v1/navigation/route` | Create Navigation Route | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `GET` | `/api/v1/notifications` | List Notifications | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `GET` | `/api/v1/notifications/` | List Notifications | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `PUT` | `/api/v1/notifications/read-all` | Mark All As Read | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `POST` | `/api/v1/notifications/register-token` | Register Device Token | Bearer (route may restrict role) | application/json: TokenRegisterRequest | 200 (application/json: —) |
| `GET` | `/api/v1/notifications/unread` | Get Unread Count | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `DELETE` | `/api/v1/notifications/unregister-token/{token}` | Unregister Device Token | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `DELETE` | `/api/v1/notifications/{id}` | Delete Notification | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `PUT` | `/api/v1/notifications/{id}/read` | Mark As Read | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `GET` | `/api/v1/patients/emergency-contact` | Get Emergency Contact | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `PUT` | `/api/v1/patients/emergency-contact` | Update Emergency Contact | Bearer (route may restrict role) | —query: name, phone | 200 (application/json: —) |
| `GET` | `/api/v1/patients/history` | Get History | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `POST` | `/api/v1/patients/medical-history` | Add Medical History | Bearer (route may restrict role) | —query: notes | 200 (application/json: —) |
| `GET` | `/api/v1/patients/profile` | Get Profile | Bearer (route may restrict role) | — | 200 (application/json: PatientProfile) |
| `PUT` | `/api/v1/patients/profile` | Update Profile | Bearer (route may restrict role) | application/json: PatientProfileUpdate | 200 (application/json: —) |
| `GET` | `/api/v1/patients/qr-code` | Get Patient Qr Code | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `GET` | `/api/v1/patients/vitals` | Get Patient Vitals | Bearer (route may restrict role) | —query: patient_id | 200 (application/json: —) |
| `POST` | `/api/v1/patients/vitals` | Record Patient Vitals | Bearer (route may restrict role) | application/json: PatientVitalsCreate | 201 (application/json: PatientVitals) |
| `GET` | `/api/v1/pharmacy/inventory` | Check Inventory | Bearer (route may restrict role) | —query: query, page, limit | 200 (application/json: —) |
| `PATCH` | `/api/v1/pharmacy/inventory/{item_id}` | Update Inventory | Bearer (route may restrict role) | —query: quantity_change, quantity_in_stock | 200 (application/json: —) |
| `PUT` | `/api/v1/pharmacy/inventory/{item_id}` | Update Inventory | Bearer (route may restrict role) | —query: quantity_change, quantity_in_stock | 200 (application/json: —) |
| `GET` | `/api/v1/pharmacy/orders` | Get Pharmacy Orders | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `GET` | `/api/v1/pharmacy/prescriptions` | List Prescriptions | Bearer (route may restrict role) | —query: patient_id | 200 (application/json: array of Prescription) |
| `POST` | `/api/v1/pharmacy/prescriptions` | Create Prescription | Bearer (route may restrict role) | application/json: app__schemas__pharmacy__PrescriptionCreate | 200 (application/json: Prescription) |
| `GET` | `/api/v1/pharmacy/prescriptions/patient/{patient_id}` | Get Patient Prescriptions | Bearer (route may restrict role) | — | 200 (application/json: array of Prescription) |
| `POST` | `/api/v1/pharmacy/prescriptions/{prescription_id}/fulfill` | Fulfill Prescription | Bearer (route may restrict role) | — | 200 (application/json: Prescription) |
| `POST` | `/api/v1/pharmacy/refill` | Request Refill | Bearer (route may restrict role) | —query: prescription_id | 200 (application/json: —) |
| `PUT` | `/api/v1/queue/complete/{appointment_id}` | Complete Queue Item | Bearer (route may restrict role) | — | 200 (application/json: Appointment) |
| `POST` | `/api/v1/queue/join/{appointment_id}` | Join Queue | Bearer (route may restrict role) | — | 200 (application/json: Appointment) |
| `POST` | `/api/v1/queue/next/{doctor_id}` | Call Next Patient | Bearer (route may restrict role) | — | 200 (application/json: Appointment) |
| `GET` | `/api/v1/queue/status` | Queue Status | Bearer (route may restrict role) | —query: doctor_id | 200 (application/json: —) |
| `GET` | `/api/v1/queue/wait-time/{doctor_id}` | Get Estimated Wait | Bearer (route may restrict role) | —query: position | 200 (application/json: —) |
| `POST` | `/api/v1/staff/admissions` | Admit Patient | Bearer; staff | application/json: AdmissionCreate | 201 (application/json: —) |
| `POST` | `/api/v1/staff/appointments` | Create Staff Appointment | Bearer; staff | application/json: app__api__v1__endpoints__staff__frontdesk__AppointmentCreate | 201 (application/json: —) |
| `GET` | `/api/v1/staff/attendance` | Attendance | Bearer; staff | — | 200 (application/json: —) |
| `DELETE` | `/api/v1/staff/devices/{device_id}` | Deactivate Device | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/doctor/labs/pending` | Pending Labs | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/doctor/prescriptions/pending` | Pending Prescriptions | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/doctor/queue` | Doctor Queue | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/doctor/schedule` | Schedule | Bearer; staff | —query: date | 200 (application/json: —) |
| `GET` | `/api/v1/staff/doctor/stats/today` | Doctor Today Stats | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/doctors/availability` | Doctor Availability | Bearer; staff | —query: doctor_id, date | 200 (application/json: —) |
| `GET` | `/api/v1/staff/doctors/load` | Doctor Load | Bearer; staff | —query: date | 200 (application/json: —) |
| `GET` | `/api/v1/staff/emergency/active` | Active Emergencies | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/emergency/{emergency_id}` | Emergency Details | Bearer; staff | — | 200 (application/json: —) |
| `POST` | `/api/v1/staff/emergency/{emergency_id}/assign` | Assign Responder | Bearer; staff | application/json: AssignResponder | 200 (application/json: —) |
| `POST` | `/api/v1/staff/emergency/{emergency_id}/message` | Send Emergency Message | Bearer; staff | application/json: MessageCreate | 201 (application/json: —) |
| `PUT` | `/api/v1/staff/emergency/{emergency_id}/status` | Update Emergency Status | Bearer; staff | application/json: StatusUpdate | 200 (application/json: —) |
| `GET` | `/api/v1/staff/facilities/beds` | List Beds | Bearer; staff | —query: ward | 200 (application/json: —) |
| `PUT` | `/api/v1/staff/facilities/beds/{bed_id}/status` | Update Bed Status | Bearer; staff | application/json: BedStatusUpdate | 200 (application/json: —) |
| `GET` | `/api/v1/staff/facilities/equipment` | Equipment List | Bearer; staff | — | 200 (application/json: —) |
| `POST` | `/api/v1/staff/facilities/maintenance` | Create Maintenance Request | Bearer; staff | application/json: MaintenanceCreate | 201 (application/json: —) |
| `GET` | `/api/v1/staff/facilities/or-schedule` | Operating Room Schedule | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/facilities/roster` | Facilities Roster | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/facilities/wards/{ward_id}/beds` | List Ward Beds | Bearer; staff | — | 200 (application/json: —) |
| `POST` | `/api/v1/staff/lab-orders` | Create Lab Order | Bearer; staff | application/json: LabOrderCreate | 201 (application/json: —) |
| `POST` | `/api/v1/staff/leave` | Request Leave | Bearer; staff | application/json: LeaveCreate | 201 (application/json: —) |
| `GET` | `/api/v1/staff/notifications` | Staff Notifications | Bearer; staff | — | 200 (application/json: —) |
| `PUT` | `/api/v1/staff/notifications/{notification_id}/read` | Mark Staff Notification Read | Bearer; staff | — | 200 (application/json: —) |
| `POST` | `/api/v1/staff/nurse/handover` | Submit Handover | Bearer; staff | application/json: object | 201 (application/json: —) |
| `POST` | `/api/v1/staff/nurse/medications/record` | Record Medication | Bearer; staff | application/json: object | 201 (application/json: —) |
| `POST` | `/api/v1/staff/nurse/vitals` | Record Vitals | Bearer; staff | application/json: PatientVitalsCreate | 201 (application/json: —) |
| `GET` | `/api/v1/staff/nurse/ward/{ward_id}/beds` | Ward Beds | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/nurse/ward/{ward_id}/medications/due` | Medications Due | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/nurse/ward/{ward_id}/vitals/due` | Vitals Due | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/patients/search` | Search Patients | Bearer; staff | —query: q | 200 (application/json: —) |
| `POST` | `/api/v1/staff/patients/walk-in` | Register Walk In | Bearer; staff | application/json: WalkInCreate | 201 (application/json: —) |
| `GET` | `/api/v1/staff/patients/{patient_id}` | Patient Detail | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/patients/{patient_id}/history` | Patient History | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/patients/{patient_id}/labs` | Patient Labs | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/patients/{patient_id}/prescriptions` | Patient Prescriptions | Bearer; staff | — | 200 (application/json: —) |
| `GET` | `/api/v1/staff/patients/{patient_id}/vitals` | Patient Vitals | Bearer; staff | — | 200 (application/json: —) |
| `POST` | `/api/v1/staff/payments` | Create Billing Record | Bearer; staff | application/json: app__api__v1__endpoints__staff__frontdesk__BillingCreate | 201 (application/json: —) |
| `POST` | `/api/v1/staff/pharmacy/dispense/{prescription_id}` | Dispense | Bearer; staff | — | 200 (application/json: —) |
| `POST` | `/api/v1/staff/pharmacy/interaction-check` | Interaction Check | Bearer; staff | application/json: InteractionCheck | 200 (application/json: —) |
| `GET` | `/api/v1/staff/pharmacy/inventory` | Inventory | Bearer; staff | —query: low_stock, barcode | 200 (application/json: —) |
| `POST` | `/api/v1/staff/pharmacy/notify-pickup` | Notify Pickup | Bearer; staff | application/json: PickupNotification | 200 (application/json: —) |
| `GET` | `/api/v1/staff/pharmacy/prescriptions` | Prescription Queue | Bearer; staff | — | 200 (application/json: —) |
| `POST` | `/api/v1/staff/pharmacy/refill/{prescription_id}/approve` | Approve Refill | Bearer; staff | — | 200 (application/json: —) |
| `POST` | `/api/v1/staff/prescriptions` | Create Prescription | Bearer; staff | application/json: app__api__v1__endpoints__staff__prescriptions__PrescriptionCreate | 201 (application/json: —) |
| `GET` | `/api/v1/staff/profile` | Get Staff Profile | Bearer; staff | — | 200 (application/json: StaffProfileResponse) |
| `PUT` | `/api/v1/staff/profile` | Update Staff Profile | Bearer; staff | application/json: StaffProfileUpdate | 200 (application/json: StaffProfileResponse) |
| `PUT` | `/api/v1/staff/queue/reorder` | Reorder Queue | Bearer; staff | application/json: QueueReorder | 200 (application/json: —) |
| `POST` | `/api/v1/staff/queue/{appointment_id}/no-show` | Mark No Show | Bearer; staff | — | 200 (application/json: —) |
| `PUT` | `/api/v1/staff/queue/{appointment_id}/status` | Update Queue Status | Bearer; staff | application/json: QueueStatusUpdate | 200 (application/json: —) |
| `POST` | `/api/v1/staff/referrals` | Create Referral | Bearer; staff | application/json: ReferralCreate | 201 (application/json: —) |
| `GET` | `/api/v1/staff/settings` | Get Staff Settings | Bearer; staff | — | 200 (application/json: —) |
| `PUT` | `/api/v1/staff/settings` | Update Staff Settings | Bearer; staff | application/json: SettingsUpdate | 200 (application/json: —) |
| `GET` | `/api/v1/staff/shifts/current` | Current Shift | Bearer; staff | — | 200 (application/json: —) |
| `POST` | `/api/v1/staff/shifts/swap` | Request Shift Swap | Bearer; staff | application/json: ShiftSwapCreate | 201 (application/json: —) |
| `GET` | `/api/v1/voice/health` | Voice services health check | Bearer (route may restrict role) | — | 200 (application/json: —) |
| `POST` | `/api/v1/voice/process` | Full Voice Loop: Audio → STT → AI Brain → TTS Response | Bearer (route may restrict role) | multipart/form-data: Body_process_voice_command_api_v1_voice_process_post | 200 (application/json: VoiceProcessResponse) |
| `POST` | `/api/v1/voice/process-text` | Text Command (no audio) → AI Brain → Optional TTS Response | Bearer (route may restrict role) | application/json: TextQueryRequest; query: return_audio | 200 (application/json: VoiceProcessResponse) |
| `POST` | `/api/v1/voice/synthesize` | Text-to-Speech only | Bearer (route may restrict role) | application/json: SynthesizeRequest | 200 (application/json: SynthesizeResponse) |
| `POST` | `/api/v1/voice/transcribe` | Speech-to-Text only | Bearer (route may restrict role) | multipart/form-data: Body_transcribe_audio_api_v1_voice_transcribe_post | 200 (application/json: —) |
| `GET` | `/debug/sentry` | Debug Sentry | Public / separately guarded | — | 200 (application/json: —) |
| `GET` | `/health` | Liveness | Public / separately guarded | — | 200 (application/json: —) |
| `HEAD` | `/health` | Liveness | Public / separately guarded | — | 200 (application/json: —) |
| `GET` | `/health/detailed` | Detailed Health | Public / separately guarded | — | 200 (application/json: —) |
| `HEAD` | `/health/detailed` | Detailed Health | Public / separately guarded | — | 200 (application/json: —) |
| `GET` | `/health/details` | Health Details | Public / separately guarded | — | 200 (application/json: —) |
| `GET` | `/metrics` | Metrics | Public / separately guarded | — | 200 (application/json: —) |
| `GET` | `/ready` | Readiness | Public / separately guarded | — | 200 (application/json: —) |
| `HEAD` | `/ready` | Readiness | Public / separately guarded | — | 200 (application/json: —) |

## Schemas and full payload fields

The endpoint table gives request body schema names and successful status codes. Use the OpenAPI document at `/api/v1/openapi.json` for field-level types, required/optional fields, validation constraints, and full response schema definitions. This document intentionally does not reproduce a second, potentially stale copy of those schemas.
