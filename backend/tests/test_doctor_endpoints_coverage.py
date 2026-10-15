from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import String

from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.doctor import Department, Doctor
from app.models.hospital import StaffSchedule
from app.models.patient import Patient
from app.models.user import User


@pytest.fixture
async def doctor_api_context(db_session, monkeypatch):
    monkeypatch.setattr(Department.__table__.c.location, "type", String())
    patient_user = User(phone="9800008801", email="patient.doctor.api@tests.example", password_hash="hash", role="patient")
    doctor_user = User(phone="9800008802", email="doctor.api@tests.example", password_hash="hash", role="doctor")
    orphan_doctor_user = User(phone="9800008803", email="orphan.doctor.api@tests.example", password_hash="hash", role="doctor")
    other_doctor_user = User(phone="9800008804", email="other.doctor.api@tests.example", password_hash="hash", role="doctor")
    department = Department(name="Doctor API Tests", floor=2, building="A", wing="North", phone="222", email="doctor-api@tests.example")
    db_session.add_all([patient_user, doctor_user, orphan_doctor_user, other_doctor_user, department])
    await db_session.flush()
    patient = Patient(user_id=patient_user.id, first_name="Patient", last_name="One", date_of_birth=datetime(1990, 1, 1), gender="unknown", emergency_contact="", emergency_contact_name="")
    doctor = Doctor(user_id=doctor_user.id, first_name="Doc", last_name="One", specialization="General", department_id=department.id, license_number="DOCTOR-API-1", years_of_experience=5, avg_consultation_time=20)
    other_doctor = Doctor(user_id=other_doctor_user.id, first_name="Doc", last_name="Two", specialization="Cardiology", department_id=department.id, license_number="DOCTOR-API-2", years_of_experience=8, is_available=False)
    db_session.add_all([patient, doctor, other_doctor])
    await db_session.flush()
    schedule = StaffSchedule(staff_id=doctor_user.id, date=datetime(2035, 6, 15), start_time=datetime(2035, 6, 15, 9), end_time=datetime(2035, 6, 15, 10), is_available=True)
    appointment = Appointment(patient_id=patient.id, doctor_id=doctor.id, department_id=department.id, scheduled_time=datetime(2035, 6, 15, 9), status="scheduled", queue_position=1, wait_time_minutes=20, notes="Initial note")
    db_session.add_all([schedule, appointment])
    await db_session.commit()

    def headers(user):
        return {"Authorization": f"Bearer {create_access_token(subject=user.id, claims={'role': user.role})}"}

    return {"patient": patient, "patient_user": patient_user, "doctor": doctor, "doctor_user": doctor_user,
            "orphan_user": orphan_doctor_user, "other_doctor": other_doctor, "department": department,
            "appointment": appointment, "headers": headers(doctor_user), "patient_headers": headers(patient_user)}


@pytest.mark.asyncio
async def test_doctor_profile_read_update_and_validation(async_client: AsyncClient, doctor_api_context):
    ctx = doctor_api_context
    profile = await async_client.get("/api/v1/doctors/profile", headers=ctx["headers"])
    update = await async_client.put("/api/v1/doctors/profile", headers=ctx["headers"], json={"first_name": " Updated ", "phone": " 9800008810 "})
    empty = await async_client.put("/api/v1/doctors/profile", headers=ctx["headers"], json={})
    invalid = await async_client.put("/api/v1/doctors/profile", headers=ctx["headers"], json={"specialization": "  "})
    assert profile.status_code == 200 and profile.json()["specialization"] == "General"
    assert update.status_code == 200 and update.json()["first_name"] == "Updated" and update.json()["phone"] == "9800008810"
    assert (empty.status_code, empty.json()["detail"]) == (422, "At least one profile field is required.")
    assert invalid.status_code == 422 and "cannot be empty" in invalid.json()["detail"]


@pytest.mark.asyncio
async def test_doctor_profile_missing_and_duplicate_phone(async_client: AsyncClient, doctor_api_context, db_session):
    ctx = doctor_api_context
    missing_headers = {"Authorization": f"Bearer {create_access_token(subject=ctx['orphan_user'].id, claims={'role': 'doctor'})}"}
    missing = await async_client.get("/api/v1/doctors/profile", headers=missing_headers)
    duplicate = await async_client.put("/api/v1/doctors/profile", headers=ctx["headers"], json={"phone": "9800008801"})
    assert (missing.status_code, missing.json()["detail"]) == (404, "Doctor profile not found.")
    assert (duplicate.status_code, duplicate.json()["detail"]) == (409, "This phone number is already in use.")


@pytest.mark.asyncio
async def test_doctor_schedule_create_overlap_invalid_and_missing_profile(async_client: AsyncClient, doctor_api_context, db_session):
    ctx = doctor_api_context
    listed = await async_client.get("/api/v1/doctors/schedule", headers=ctx["headers"])
    created = await async_client.post("/api/v1/doctors/schedule", headers=ctx["headers"], json={"date": "2035-06-16", "start_time": "09:00:00", "end_time": "12:00:00", "shift_type": "clinic"})
    overlap = await async_client.post("/api/v1/doctors/schedule", headers=ctx["headers"], json={"date": "2035-06-15", "start_time": "09:30:00", "end_time": "11:00:00"})
    invalid = await async_client.post("/api/v1/doctors/schedule", headers=ctx["headers"], json={"date": "2035-06-17", "start_time": "12:00:00", "end_time": "09:00:00"})
    no_profile_headers = {"Authorization": f"Bearer {create_access_token(subject=ctx['orphan_user'].id, claims={'role': 'doctor'})}"}
    missing = await async_client.post("/api/v1/doctors/schedule", headers=no_profile_headers, json={"date": "2035-06-17", "start_time": "09:00:00", "end_time": "12:00:00"})
    assert listed.status_code == 200 and len(listed.json()["items"]) == 1
    assert created.status_code == 201 and created.json()["shift_type"] == "clinic"
    assert (overlap.status_code, overlap.json()["detail"]) == (409, "Schedule overlaps an existing shift.")
    assert (invalid.status_code, invalid.json()["detail"]) == (422, "Schedule start_time must precede end_time.")
    assert (missing.status_code, missing.json()["detail"]) == (404, "Doctor profile not found.")


@pytest.mark.asyncio
async def test_doctor_notes_are_scoped_to_assigned_appointments(async_client: AsyncClient, doctor_api_context):
    ctx = doctor_api_context
    notes = await async_client.get(f"/api/v1/doctors/patients/{ctx['patient'].id}/notes", headers=ctx["headers"])
    saved = await async_client.post(f"/api/v1/doctors/patients/{ctx['patient'].id}/notes", headers=ctx["headers"], json={"appointment_id": ctx["appointment"].id, "notes": "Follow-up notes"})
    missing_patient = await async_client.get("/api/v1/doctors/patients/99999/notes", headers=ctx["headers"])
    assert notes.json()["items"][0]["notes"] == "Initial note"
    assert saved.status_code == 200 and saved.json()["notes"] == "Follow-up notes"
    assert (missing_patient.status_code, missing_patient.json()["detail"]) == (404, "Patient profile not found.")


@pytest.mark.asyncio
async def test_public_doctor_lists_and_availability(async_client: AsyncClient, doctor_api_context):
    ctx = doctor_api_context
    all_doctors = await async_client.get("/api/v1/doctors", headers=ctx["headers"])
    available = await async_client.get("/api/v1/doctors/available", headers=ctx["headers"])
    by_department = await async_client.get(f"/api/v1/doctors/department/{ctx['department'].id}", headers=ctx["headers"])
    detail = await async_client.get(f"/api/v1/doctors/{ctx['doctor'].id}", headers=ctx["headers"])
    date_slots = await async_client.get(f"/api/v1/doctors/{ctx['doctor'].id}/availability?date=2035-06-15", headers=ctx["headers"])
    missing = await async_client.get("/api/v1/doctors/99999", headers=ctx["headers"])
    assert all_doctors.status_code == 200 and len(all_doctors.json()) == 2
    assert len(available.json()) == 1 and available.json()[0]["id"] == ctx["doctor"].id
    assert len(by_department.json()) == 2 and detail.json()["department"]["name"] == "Doctor API Tests"
    assert date_slots.json()["is_available"] is True and "2035-06-15T09:20:00" in date_slots.json()["available_slots"]
    assert (missing.status_code, missing.json()["detail"]) == (404, "Doctor not found")


@pytest.mark.asyncio
async def test_doctor_availability_update_is_owner_scoped(async_client: AsyncClient, doctor_api_context):
    ctx = doctor_api_context
    updated = await async_client.put(f"/api/v1/doctors/availability?id={ctx['doctor'].id}&available=false", headers=ctx["headers"])
    foreign = await async_client.put(f"/api/v1/doctors/availability?id={ctx['other_doctor'].id}&available=true", headers=ctx["headers"])
    missing = await async_client.put("/api/v1/doctors/availability?id=99999&available=true", headers=ctx["headers"])
    assert updated.json() == {"message": "Availability updated"}
    assert (foreign.status_code, foreign.json()["detail"]) == (403, "You can only update your own availability.")
    assert (missing.status_code, missing.json()["detail"]) == (404, "Doctor not found")
