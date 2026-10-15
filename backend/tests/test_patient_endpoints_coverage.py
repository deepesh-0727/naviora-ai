from datetime import datetime

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.doctor import Department, Doctor
from app.models.patient import Patient
from app.models.pharmacy import Prescription
from app.models.user import User
from app.models.vitals import PatientVitals


@pytest.fixture
async def patient_api_context(db_session):
    patient_user = User(phone="+919800008801", email="patient.api@tests.example", password_hash="hash", role="patient")
    other_patient_user = User(phone="+919800008802", email="other.patient.api@tests.example", password_hash="hash", role="patient")
    doctor_user = User(phone="+919800008803", email="doctor.patient.api@tests.example", password_hash="hash", role="doctor")
    nurse_user = User(phone="+919800008804", email="nurse.patient.api@tests.example", password_hash="hash", role="nurse")
    department = Department(name="Patient API Tests", floor=1, building="A", wing="West", phone="111", email="patient-api@tests.example")
    db_session.add_all([patient_user, other_patient_user, doctor_user, nurse_user, department])
    await db_session.flush()
    patient = Patient(
        user_id=patient_user.id, first_name="Pat", last_name="One", date_of_birth=datetime(1990, 5, 4), gender="unknown",
        blood_group="O+", allergies=["pollen"], emergency_contact="9876543210", emergency_contact_name="Contact",
        medical_history="Asthma", insurance_provider="Care", insurance_number="POLICY-1",
    )
    other_patient = Patient(
        user_id=other_patient_user.id, first_name="Pat", last_name="Two", date_of_birth=datetime(1991, 5, 4), gender="female",
        emergency_contact="9876543211", emergency_contact_name="Other Contact",
    )
    doctor = Doctor(
        user_id=doctor_user.id, first_name="Doc", last_name="One", specialization="General", department_id=department.id,
        license_number="PATIENT-API-DOC", years_of_experience=4,
    )
    db_session.add_all([patient, other_patient, doctor])
    await db_session.flush()
    appointment = Appointment(
        patient_id=patient.id, doctor_id=doctor.id, department_id=department.id,
        scheduled_time=datetime(2025, 1, 1, 9), actual_time=datetime(2025, 1, 1, 9, 30), status="completed",
        queue_position=0, wait_time_minutes=0, symptoms="Cough", notes="Rest",
    )
    db_session.add(appointment)
    await db_session.flush()
    prescription = Prescription(
        appointment_id=appointment.id, patient_id=patient.id, doctor_id=doctor.id,
        medication="Medicine", dosage="1 tablet", frequency="daily", duration="5 days", instructions="After food",
    )
    vital = PatientVitals(
        patient_id=patient.id, recorded_by_id=doctor_user.id, blood_pressure_systolic=120,
        blood_pressure_diastolic=80, heart_rate=72, temperature=36.5, spo2=98, notes="Stable",
    )
    db_session.add_all([prescription, vital])
    await db_session.commit()

    def headers(user):
        return {"Authorization": f"Bearer {create_access_token(subject=user.id, claims={'role': user.role})}"}

    return {
        "patient": patient, "patient_user": patient_user, "other_patient": other_patient,
        "other_user": other_patient_user, "doctor": doctor, "doctor_user": doctor_user, "nurse_user": nurse_user,
        "appointment": appointment, "headers": headers(patient_user), "other_headers": headers(other_patient_user),
        "doctor_headers": headers(doctor_user), "nurse_headers": headers(nurse_user),
    }


@pytest.mark.asyncio
async def test_profile_includes_patient_data_and_completed_visit(async_client: AsyncClient, patient_api_context):
    response = await async_client.get("/api/v1/patients/profile", headers=patient_api_context["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Pat" and body["blood_group"] == "O+"
    assert body["allergies"] == ["pollen"] and body["email"] == "patient.api@tests.example"
    assert body["total_visits"] == 1 and body["last_visit_date"] == "2025-01-01"


@pytest.mark.asyncio
async def test_top_level_department_routes_match_navigation_routes(
    async_client: AsyncClient,
    patient_api_context,
):
    headers = patient_api_context["headers"]
    top_level_list = await async_client.get("/api/v1/departments", headers=headers)
    navigation_list = await async_client.get(
        "/api/v1/navigation/departments", headers=headers
    )

    assert top_level_list.status_code == 200
    assert top_level_list.json() == navigation_list.json()
    assert top_level_list.json()[0]["name"] == "Patient API Tests"

    department_id = top_level_list.json()[0]["id"]
    top_level_detail = await async_client.get(
        f"/api/v1/departments/{department_id}", headers=headers
    )
    navigation_detail = await async_client.get(
        f"/api/v1/navigation/departments/{department_id}", headers=headers
    )

    assert top_level_detail.status_code == 200
    assert top_level_detail.json() == navigation_detail.json()


@pytest.mark.asyncio
async def test_profile_missing_and_permission_denied(async_client: AsyncClient, patient_api_context, db_session):
    missing_user = User(phone="+919800008805", email="no.profile@tests.example", password_hash="hash", role="patient")
    db_session.add(missing_user)
    await db_session.commit()
    missing_headers = {"Authorization": f"Bearer {create_access_token(subject=missing_user.id, claims={'role': 'patient'})}"}
    missing = await async_client.get("/api/v1/patients/profile", headers=missing_headers)
    forbidden = await async_client.get("/api/v1/patients/profile", headers=patient_api_context["doctor_headers"])
    assert (missing.status_code, missing.json()["detail"]) == (404, "Patient profile not found.")
    assert forbidden.status_code == 403 and "lacks permission" in forbidden.json()["detail"]


@pytest.mark.asyncio
async def test_update_profile_persists_fields_and_rejects_empty_or_duplicate(async_client: AsyncClient, patient_api_context, db_session):
    ctx = patient_api_context
    updated = await async_client.put("/api/v1/patients/profile", headers=ctx["headers"], json={"first_name": "Updated", "phone": "+919800008899", "date_of_birth": "1990-05-04"})
    await db_session.refresh(ctx["patient"])
    empty = await async_client.put("/api/v1/patients/profile", headers=ctx["headers"], json={})
    duplicate = await async_client.put("/api/v1/patients/profile", headers=ctx["headers"], json={"email": "other.patient.api@tests.example"})
    assert updated.status_code == 200 and updated.json()["message"] == "Profile updated successfully"
    assert ctx["patient"].first_name == "Updated" and ctx["patient_user"].phone == "9800008899"
    assert (empty.status_code, empty.json()["detail"]) == (422, "At least one profile field is required.")
    assert (duplicate.status_code, duplicate.json()["detail"]) == (409, "Email is already in use.")


@pytest.mark.asyncio
async def test_patient_history_contains_visits_prescriptions_and_notes(async_client: AsyncClient, patient_api_context):
    response = await async_client.get("/api/v1/patients/history", headers=patient_api_context["headers"])
    assert response.status_code == 200
    history = response.json()["history"]
    by_type = {item["type"]: item for item in history}
    assert set(by_type) == {"visit", "prescription", "notes"}
    assert by_type["visit"]["doctor"] == "Dr. Doc One"
    assert by_type["prescription"]["diagnosis"] == "Prescription: Medicine"


@pytest.mark.asyncio
async def test_medical_history_and_emergency_contact_routes(async_client: AsyncClient, patient_api_context, db_session):
    ctx = patient_api_context
    added = await async_client.post("/api/v1/patients/medical-history", headers=ctx["headers"], params={"notes": "New allergy"})
    contact = await async_client.get("/api/v1/patients/emergency-contact", headers=ctx["headers"])
    changed = await async_client.put("/api/v1/patients/emergency-contact", headers=ctx["headers"], params={"name": "Updated Contact", "phone": "9999999999"})
    await db_session.refresh(ctx["patient"])
    assert added.json() == {"message": "Medical history added", "notes": "New allergy"}
    assert ctx["patient"].medical_history == "Asthma\nNew allergy"
    assert contact.json() == {"name": "Contact", "phone": "9876543210"}
    assert changed.json() == {"message": "Emergency contact updated successfully"}
    assert ctx["patient"].emergency_contact_name == "Updated Contact"


@pytest.mark.asyncio
async def test_emergency_contact_missing_profile_and_qr_code(async_client: AsyncClient, patient_api_context, db_session):
    ctx = patient_api_context
    missing_user = User(phone="+919800008806", email="contact.no.profile@tests.example", password_hash="hash", role="patient")
    db_session.add(missing_user)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(subject=missing_user.id, claims={'role': 'patient'})}"}
    contact = await async_client.get("/api/v1/patients/emergency-contact", headers=headers)
    qr = await async_client.get("/api/v1/patients/qr-code", headers=ctx["headers"])
    assert contact.json() == {"name": "Not set", "phone": ""}
    assert qr.json() == {"qr_data": f"NAVIORA-{ctx['patient_user'].id}", "label": "Show this at reception"}


@pytest.mark.asyncio
async def test_patient_vitals_access_and_staff_entry(async_client: AsyncClient, patient_api_context):
    ctx = patient_api_context
    own = await async_client.get("/api/v1/patients/vitals", headers=ctx["headers"])
    wrong_id = await async_client.get(f"/api/v1/patients/vitals?patient_id={ctx['other_patient'].id}", headers=ctx["headers"])
    missing_id = await async_client.get("/api/v1/patients/vitals?patient_id=99999", headers=ctx["nurse_headers"])
    inserted = await async_client.post("/api/v1/patients/vitals", headers=ctx["nurse_headers"], json={
        "patient_id": ctx["patient"].id, "blood_pressure_systolic": 118, "blood_pressure_diastolic": 78,
        "heart_rate": 70, "temperature": 36.6, "spo2": 99, "notes": "Follow-up",
    })
    assert own.status_code == 200 and own.json()["items"][0]["notes"] == "Stable"
    assert (wrong_id.status_code, wrong_id.json()["detail"]) == (403, "You may only access your own vitals.")
    assert (missing_id.status_code, missing_id.json()["detail"]) == (404, "Patient profile not found.")
    assert inserted.status_code == 201 and inserted.json()["recorded_by_id"] == ctx["nurse_user"].id


@pytest.mark.asyncio
async def test_doctor_vitals_require_assigned_patient_and_patient_cannot_write(async_client: AsyncClient, patient_api_context):
    ctx = patient_api_context
    doctor_read = await async_client.get(f"/api/v1/patients/vitals?patient_id={ctx['patient'].id}", headers=ctx["doctor_headers"])
    denied = await async_client.get(f"/api/v1/patients/vitals?patient_id={ctx['other_patient'].id}", headers=ctx["doctor_headers"])
    patient_write = await async_client.post("/api/v1/patients/vitals", headers=ctx["headers"], json={
        "patient_id": ctx["patient"].id, "blood_pressure_systolic": 120, "blood_pressure_diastolic": 80,
        "heart_rate": 72, "temperature": 36.5, "spo2": 98,
    })
    assert doctor_read.status_code == 200 and len(doctor_read.json()["items"]) == 1
    assert (denied.status_code, denied.json()["detail"]) == (403, "You are not assigned to this patient.")
    assert (patient_write.status_code, patient_write.json()["detail"]) == (403, "Vitals entry is not authorized.")


@pytest.mark.asyncio
async def test_vitals_require_staff_target_and_doctor_profile(async_client: AsyncClient, patient_api_context, db_session):
    ctx = patient_api_context
    no_target = await async_client.get("/api/v1/patients/vitals", headers=ctx["nurse_headers"])
    no_doctor_profile_user = User(phone="+919800008807", email="not.doctor.profile@tests.example", password_hash="hash", role="doctor")
    db_session.add(no_doctor_profile_user)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(subject=no_doctor_profile_user.id, claims={'role': 'doctor'})}"}
    no_doctor = await async_client.get(f"/api/v1/patients/vitals?patient_id={ctx['patient'].id}", headers=headers)
    assert (no_target.status_code, no_target.json()["detail"]) == (422, "patient_id is required for staff access.")
    assert (no_doctor.status_code, no_doctor.json()["detail"]) == (404, "Doctor profile not found.")
