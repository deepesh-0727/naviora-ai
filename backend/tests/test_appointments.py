"""
Unit tests for /api/v1/appointments/* endpoints.

Auth-protected endpoints are tested for:
  - 401 when no token provided
  - correct queue/availability data shapes
"""
import pytest


# ---------------------------------------------------------------------------
# Unauthenticated access guards
# ---------------------------------------------------------------------------

def test_list_appointments_unauthorized(client):
    """GET /appointments without a token must return 401."""
    resp = client.get("/api/v1/appointments")
    assert resp.status_code == 401


def test_get_single_appointment_unauthorized(client):
    """GET /appointments/{id} without a token must return 401."""
    resp = client.get("/api/v1/appointments/1")
    assert resp.status_code == 401


def test_book_appointment_unauthorized(client):
    """POST /appointments without a token must return 401."""
    resp = client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": 1,
            "department_id": 1,
            "scheduled_time": "2026-09-10T10:00:00",
        },
    )
    assert resp.status_code == 401


def test_cancel_appointment_unauthorized(client):
    """DELETE /appointments/{id} without a token must return 401."""
    resp = client.delete("/api/v1/appointments/1")
    assert resp.status_code == 401


def test_update_appointment_unauthorized(client):
    """PUT /appointments/{id} without a token must return 401."""
    resp = client.put(
        "/api/v1/appointments/1",
        json={"status": "cancelled"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Queue status
# ---------------------------------------------------------------------------

def test_get_queue_status_unauthorized(client):
    """GET /appointments/queue without a token must return 401."""
    resp = client.get("/api/v1/appointments/queue")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Doctor availability (does NOT require auth)
# ---------------------------------------------------------------------------

def test_get_doctor_availability_unknown_doctor(client):
    """Requesting availability for a non-existent doctor should return 404."""
    resp = client.get("/api/v1/appointments/doctor/999999/availability")
    assert resp.status_code == 404


def test_get_doctor_availability_response_shape(client, db_session):
    """
    If a doctor exists, the availability response must contain the expected keys.
    This is a schema-level test using an in-memory DB seeded with a doctor row.
    """
    from app.models.doctor import Doctor

    # Seed a minimal doctor row into the in-memory SQLite DB.
    doctor = Doctor(
        first_name="Test",
        last_name="Doctor",
        specialization="General",
        is_available=True,
        max_patients_per_day=30,
        current_patients=5,
        avg_consultation_time=15,
        consultation_fee=500.0,
    )
    import asyncio
    asyncio.get_event_loop().run_until_complete(_seed_doctor(db_session, doctor))

    resp = client.get(f"/api/v1/appointments/doctor/{doctor.id}/availability")
    assert resp.status_code == 200
    body = resp.json()
    assert "doctor_id" in body
    assert "is_available" in body
    assert "available_slots" in body
    assert isinstance(body["available_slots"], list)


async def _seed_doctor(session, doctor):
    session.add(doctor)
    await session.commit()
    await session.refresh(doctor)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_book_appointment_missing_fields_unauthorized(client):
    """Booking with missing required fields should still fail at auth (401), not 422,
    because auth runs before body validation in FastAPI."""
    resp = client.post("/api/v1/appointments", json={})
    # No token → 401 before schema validation runs
    assert resp.status_code == 401
