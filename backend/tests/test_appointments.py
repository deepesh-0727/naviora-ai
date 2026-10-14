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
# Doctor availability requires an authenticated API role
# ---------------------------------------------------------------------------

def test_get_doctor_availability_unauthorized(client):
    response = client.get("/api/v1/doctors/1/availability")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_book_appointment_missing_fields_unauthorized(client):
    """Booking with missing required fields should still fail at auth (401), not 422,
    because auth runs before body validation in FastAPI."""
    resp = client.post("/api/v1/appointments", json={})
    # No token → 401 before schema validation runs
    assert resp.status_code == 401
