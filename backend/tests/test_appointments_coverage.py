from datetime import datetime
from unittest.mock import AsyncMock

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
async def appointment_context(db_session, monkeypatch, deterministic_appointment_time):
    from app.api.v1.endpoints import appointments as appointments_module

    connection = await db_session.connection()
    sqlite_connection = connection.sync_connection.connection.driver_connection
    await sqlite_connection.create_function("ST_AsEWKB", 1, lambda _value: None)
    monkeypatch.setattr(Department.__table__.c.location, "type", String())
    monkeypatch.setattr(appointments_module.limiter, "enabled", False, raising=False)
    broadcast = AsyncMock(return_value=True)
    monkeypatch.setattr(appointments_module.ws_manager, "broadcast_event", broadcast)
    patient_user = User(phone="+919800006601", email="appointments.patient@tests.example", password_hash="hash", role="patient")
    other_user = User(phone="+919800006602", email="appointments.other@tests.example", password_hash="hash", role="patient")
    doctor_user = User(phone="+919800006603", email="appointments.doctor@tests.example", password_hash="hash", role="doctor")
    unavailable_doctor_user = User(phone="+919800006605", email="appointments.unavailable-doctor@tests.example", password_hash="hash", role="doctor")
    department = Department(name="Appointments Tests", floor=2, building="B", wing="North", phone="101", email="appointments@tests.example")
    other_department = Department(name="Other Appointments", floor=3, building="B", wing="South", phone="102", email="other-appointments@tests.example")
    db_session.add_all([patient_user, other_user, doctor_user, unavailable_doctor_user, department, other_department])
    await db_session.flush()
    patient = Patient(
        user_id=patient_user.id,
        first_name="Appointment",
        last_name="Patient",
        date_of_birth=datetime(1990, 1, 1),
        gender="unknown",
        emergency_contact="",
        emergency_contact_name="",
    )
    other_patient = Patient(
        user_id=other_user.id,
        first_name="Other",
        last_name="Patient",
        date_of_birth=datetime(1992, 1, 1),
        gender="unknown",
        emergency_contact="",
        emergency_contact_name="",
    )
    doctor = Doctor(
        user_id=doctor_user.id,
        first_name="Asha",
        last_name="Doctor",
        specialization="General",
        department_id=department.id,
        license_number="APPOINTMENT-DOCTOR-1",
        years_of_experience=7,
        avg_consultation_time=20,
        max_patients_per_day=20,
    )
    unavailable_doctor = Doctor(
        user_id=unavailable_doctor_user.id,
        first_name="Unavailable",
        last_name="Doctor",
        specialization="General",
        department_id=department.id,
        license_number="APPOINTMENT-DOCTOR-2",
        years_of_experience=5,
        is_available=False,
        avg_consultation_time=20,
    )
    db_session.add_all([patient, other_patient, doctor, unavailable_doctor])
    await db_session.flush()
    schedule = StaffSchedule(
        staff_id=doctor_user.id,
        date=datetime(2035, 6, 15),
        start_time=datetime(2035, 6, 15, 9),
        end_time=datetime(2035, 6, 15, 12),
        is_available=True,
    )
    appointments = [
        Appointment(patient_id=patient.id, doctor_id=doctor.id, department_id=department.id, scheduled_time=datetime(2035, 6, 15, 9), status="scheduled", queue_position=1, wait_time_minutes=20, symptoms="existing"),
        Appointment(patient_id=patient.id, doctor_id=doctor.id, department_id=department.id, scheduled_time=datetime(2033, 6, 15, 9), status="completed", queue_position=0, wait_time_minutes=0),
        Appointment(patient_id=patient.id, doctor_id=doctor.id, department_id=department.id, scheduled_time=datetime(2035, 6, 15, 9, 20), status="cancelled", queue_position=0, wait_time_minutes=0),
        Appointment(patient_id=patient.id, doctor_id=doctor.id, department_id=department.id, scheduled_time=datetime(2035, 6, 15, 9, 40), status="check_in", queue_position=2, wait_time_minutes=40),
        Appointment(patient_id=other_patient.id, doctor_id=doctor.id, department_id=department.id, scheduled_time=datetime(2035, 6, 15, 10), status="scheduled", queue_position=3, wait_time_minutes=60),
    ]
    db_session.add_all([schedule, *appointments])
    await db_session.commit()
    for appointment in appointments:
        await db_session.refresh(appointment)

    def headers(user):
        token = create_access_token(subject=user.id, claims={"role": user.role})
        return {"Authorization": f"Bearer {token}"}

    return {
        "patient_user": patient_user,
        "patient": patient,
        "other_patient": other_patient,
        "other_user": other_user,
        "doctor": doctor,
        "unavailable_doctor": unavailable_doctor,
        "department": department,
        "other_department": other_department,
        "appointments": appointments,
        "headers": headers(patient_user),
        "other_headers": headers(other_user),
        "broadcast": broadcast,
    }


@pytest.mark.asyncio
async def test_booking_creates_appointment_returns_names_and_broadcasts(async_client: AsyncClient, appointment_context):
    ctx = appointment_context
    response = await async_client.post(
        "/api/v1/appointments",
        headers=ctx["headers"],
        json={
            "doctor_id": ctx["doctor"].id,
            "department_id": ctx["department"].id,
            "scheduled_time": "2035-06-15T09:20:00",
            "symptoms": "headache",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["doctor_name"] == "Asha Doctor"
    assert body["department_name"] == "Appointments Tests"
    assert body["scheduled_time"] == "2035-06-15T09:20:00"
    assert body["status"] == "scheduled"
    assert body["queue_position"] == 3
    assert body["estimated_wait_minutes"] == 60
    fetched = await async_client.get(f"/api/v1/appointments/{body['id']}", headers=ctx["headers"])
    assert fetched.status_code == 200
    assert ctx["broadcast"].await_count == 2


@pytest.mark.asyncio
async def test_booking_rejects_past_time_wrong_department_unavailable_doctor_and_taken_slot(async_client: AsyncClient, appointment_context):
    ctx = appointment_context
    base = {"department_id": ctx["department"].id, "doctor_id": ctx["doctor"].id, "scheduled_time": "2035-06-15T10:00:00"}
    past = await async_client.post("/api/v1/appointments", headers=ctx["headers"], json={**base, "scheduled_time": "2030-06-15T10:00:00"})
    wrong_department = await async_client.post("/api/v1/appointments", headers=ctx["headers"], json={**base, "department_id": ctx["other_department"].id})
    unavailable = await async_client.post("/api/v1/appointments", headers=ctx["headers"], json={**base, "doctor_id": ctx["unavailable_doctor"].id})
    occupied = await async_client.post("/api/v1/appointments", headers=ctx["headers"], json={**base, "scheduled_time": "2035-06-15T09:00:00"})

    assert (past.status_code, past.json()["detail"]) == (422, "Appointment time must be in the future.")
    assert (wrong_department.status_code, wrong_department.json()["detail"]) == (422, "Doctor does not belong to the selected department.")
    assert (unavailable.status_code, unavailable.json()["detail"]) == (409, "Doctor is not currently accepting appointments.")
    assert (occupied.status_code, occupied.json()["detail"]) == (409, "Selected appointment time is not available.")


@pytest.mark.asyncio
async def test_booking_requires_patient_profile_and_existing_doctor(async_client: AsyncClient, appointment_context, db_session):
    ctx = appointment_context
    no_profile = User(phone="+919800006604", email="no-profile@tests.example", password_hash="hash", role="patient")
    db_session.add(no_profile)
    await db_session.commit()
    no_profile_headers = {"Authorization": f"Bearer {create_access_token(subject=no_profile.id, claims={'role': 'patient'})}"}
    missing_profile = await async_client.post("/api/v1/appointments", headers=no_profile_headers, json={"doctor_id": ctx["doctor"].id, "department_id": ctx["department"].id, "scheduled_time": "2035-06-15T10:00:00"})
    missing_doctor = await async_client.post("/api/v1/appointments", headers=ctx["headers"], json={"doctor_id": 99999, "department_id": ctx["department"].id, "scheduled_time": "2035-06-15T10:00:00"})

    assert (missing_profile.status_code, missing_profile.json()["detail"]) == (404, "Patient profile not found.")
    assert (missing_doctor.status_code, missing_doctor.json()["detail"]) == (404, "Doctor not found.")


@pytest.mark.asyncio
async def test_list_appointments_filters_upcoming_past_and_other_patient(async_client: AsyncClient, appointment_context):
    ctx = appointment_context
    all_response = await async_client.get("/api/v1/appointments", headers=ctx["headers"])
    upcoming = await async_client.get("/api/v1/appointments?upcoming=true", headers=ctx["headers"])
    past = await async_client.get("/api/v1/appointments?upcoming=false", headers=ctx["headers"])
    other = await async_client.get("/api/v1/appointments", headers=ctx["other_headers"])

    assert all_response.status_code == 200
    assert len(all_response.json()) == 4
    assert {row["status"] for row in upcoming.json()} == {"scheduled", "check_in"}
    assert {row["status"] for row in past.json()} == {"completed", "cancelled"}
    assert [row["status"] for row in other.json()] == ["scheduled"]
    assert upcoming.json()[0]["doctor_name"] == "Asha Doctor"
    assert upcoming.json()[0]["department_name"] == "Appointments Tests"


@pytest.mark.asyncio
async def test_queue_status_returns_active_rows_and_waiting_average(async_client: AsyncClient, appointment_context):
    response = await async_client.get("/api/v1/appointments/queue", headers=appointment_context["headers"])
    assert response.status_code == 200
    assert response.json() == {
        "total_waiting": 1,
        "average_wait_minutes": 40,
        "queue": [
            {"appointment_id": appointment_context["appointments"][3].id, "doctor_id": appointment_context["doctor"].id, "position": 2, "status": "check_in"}
        ],
    }


@pytest.mark.asyncio
async def test_get_appointment_returns_only_owned_record(async_client: AsyncClient, appointment_context):
    ctx = appointment_context
    owned = await async_client.get(f"/api/v1/appointments/{ctx['appointments'][0].id}", headers=ctx["headers"])
    foreign = await async_client.get(f"/api/v1/appointments/{ctx['appointments'][4].id}", headers=ctx["headers"])
    missing = await async_client.get("/api/v1/appointments/999999", headers=ctx["headers"])

    assert owned.status_code == 200
    assert owned.json()["doctor_name"] == "Asha Doctor"
    assert owned.json()["status"] == "scheduled"
    assert foreign.status_code == 404
    assert foreign.json() == {"detail": "Appointment not found."}
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Appointment not found."}


@pytest.mark.asyncio
async def test_update_appointment_changes_fields_and_reschedules_to_open_slot(async_client: AsyncClient, appointment_context, db_session):
    ctx = appointment_context
    appointment = ctx["appointments"][0]
    response = await async_client.put(
        f"/api/v1/appointments/{appointment.id}",
        headers=ctx["headers"],
        json={"scheduled_time": "2035-06-15T10:20:00", "symptoms": "updated symptom"},
    )
    await db_session.refresh(appointment)

    assert response.status_code == 200
    assert response.json() == {"message": f"Appointment {appointment.id} updated successfully"}
    assert appointment.scheduled_time == datetime(2035, 6, 15, 10, 20)
    assert appointment.symptoms == "updated symptom"


@pytest.mark.asyncio
async def test_update_appointment_rejects_empty_past_taken_foreign_and_non_scheduled(async_client: AsyncClient, appointment_context):
    ctx = appointment_context
    appointment_id = ctx["appointments"][0].id
    empty = await async_client.put(f"/api/v1/appointments/{appointment_id}", headers=ctx["headers"], json={})
    past = await async_client.put(f"/api/v1/appointments/{appointment_id}", headers=ctx["headers"], json={"scheduled_time": "2030-01-01T09:00:00"})
    taken = await async_client.put(f"/api/v1/appointments/{appointment_id}", headers=ctx["headers"], json={"scheduled_time": "2035-06-15T09:40:00"})
    foreign = await async_client.put(f"/api/v1/appointments/{ctx['appointments'][4].id}", headers=ctx["headers"], json={"symptoms": "no"})
    completed = await async_client.put(f"/api/v1/appointments/{ctx['appointments'][1].id}", headers=ctx["headers"], json={"symptoms": "no"})

    assert (empty.status_code, empty.json()["detail"]) == (422, "At least one appointment field is required.")
    assert (past.status_code, past.json()["detail"]) == (422, "Appointment time must be in the future.")
    assert (taken.status_code, taken.json()["detail"]) == (409, "Selected appointment time is not available.")
    assert (foreign.status_code, foreign.json()["detail"]) == (404, "Appointment not found.")
    assert (completed.status_code, completed.json()["detail"]) == (409, "Only scheduled appointments can be changed.")


@pytest.mark.asyncio
async def test_cancel_appointment_updates_and_broadcasts_then_rejects_repeat(async_client: AsyncClient, appointment_context, db_session):
    ctx = appointment_context
    appointment = ctx["appointments"][0]
    response = await async_client.delete(f"/api/v1/appointments/{appointment.id}", headers=ctx["headers"])
    await db_session.refresh(appointment)
    repeated = await async_client.delete(f"/api/v1/appointments/{appointment.id}", headers=ctx["headers"])
    foreign = await async_client.delete(f"/api/v1/appointments/{ctx['appointments'][4].id}", headers=ctx["headers"])

    assert response.status_code == 200
    assert response.json() == {"message": f"Appointment {appointment.id} canceled successfully"}
    assert appointment.status == "cancelled"
    assert ctx["broadcast"].await_count == 2
    assert (repeated.status_code, repeated.json()["detail"]) == (409, "Only scheduled appointments can be cancelled.")
    assert (foreign.status_code, foreign.json()["detail"]) == (404, "Appointment not found.")


@pytest.mark.asyncio
async def test_doctor_availability_returns_slots_and_missing_doctor(async_client: AsyncClient, appointment_context):
    ctx = appointment_context
    response = await async_client.get(f"/api/v1/appointments/doctor/{ctx['doctor'].id}/availability?date=2035-06-15", headers=ctx["headers"])
    missing = await async_client.get("/api/v1/appointments/doctor/99999/availability?date=2035-06-15", headers=ctx["headers"])

    assert response.status_code == 200
    assert response.json()["doctor_id"] == ctx["doctor"].id
    assert response.json()["is_available"] is True
    assert "2035-06-15T09:20:00" in response.json()["available_slots"]
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Doctor not found."}
