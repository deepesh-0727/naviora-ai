from datetime import datetime
import os
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from redis.asyncio import Redis

from app.core.security import create_access_token
from app.models.doctor import Department, Doctor
from app.models.hospital import StaffSchedule
from app.models.patient import Patient
from app.models.user import User
from app.services.ws_manager import ws_manager


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2034, 1, 1, 0, 0)
        return value.replace(tzinfo=tz) if tz else value


@pytest_asyncio.fixture
async def flush_test_redis_before_integration_test():
    """Flush only the explicitly configured test Redis database."""
    redis_url = os.getenv("NAVIORA_TEST_REDIS_URL")
    if not redis_url:
        yield
        return
    redis = Redis.from_url(redis_url, decode_responses=True)
    try:
        await redis.flushdb()
        yield
    finally:
        await redis.flushdb()
        await redis.aclose()


@pytest.fixture
def deterministic_appointment_time(monkeypatch):
    from app.api.v1.endpoints import appointments as appointments_module
    from app.services import availability_service

    monkeypatch.setattr(appointments_module, "datetime", FixedDateTime)
    monkeypatch.setattr(availability_service, "datetime", FixedDateTime)


@pytest_asyncio.fixture
async def hospital_actors(db_session, monkeypatch, flush_test_redis_before_integration_test):
    if not os.getenv("NAVIORA_TEST_REDIS_URL"):
        pytest.skip(
            "External blocker: configure NAVIORA_TEST_REDIS_URL for real-Redis-backed API integration journeys."
        )
    patient_user = User(
        phone="+919800001001", email="journey.patient@tests.example",
        password_hash="journey-password-hash", role="patient", is_active=True,
    )
    doctor_user = User(
        phone="+919800001002", email="journey.doctor@tests.example",
        password_hash="journey-password-hash", role="doctor", is_active=True,
    )
    responder = User(
        phone="+919800001003", email="journey.responder@tests.example",
        password_hash="journey-password-hash", role="emergency", is_active=True,
    )
    admin = User(
        phone="+919800001004", email="journey.admin@tests.example",
        password_hash="journey-password-hash", role="admin", is_active=True,
    )
    department = Department(
        name="Journey Department", floor=1, building="A", wing="North",
        phone="102", email="journey.department@tests.example",
    )
    db_session.add_all([patient_user, doctor_user, responder, admin, department])
    await db_session.flush()

    patient = Patient(
        user_id=patient_user.id, first_name="Patient", last_name="Journey",
        date_of_birth=datetime(1990, 1, 1), gender="unknown",
        emergency_contact="", emergency_contact_name="",
    )
    doctor = Doctor(
        user_id=doctor_user.id, first_name="Doctor", last_name="Journey",
        specialization="General", department_id=department.id,
        license_number="JOURNEY-DOCTOR-1", years_of_experience=6,
        avg_consultation_time=20, max_patients_per_day=10,
    )
    db_session.add_all([patient, doctor])
    await db_session.flush()
    db_session.add(StaffSchedule(
        staff_id=doctor_user.id, date=datetime(2035, 6, 15),
        start_time=datetime(2035, 6, 15, 9), end_time=datetime(2035, 6, 15, 12),
        is_available=True,
    ))
    await db_session.commit()

    monkeypatch.setattr(ws_manager, "broadcast_event", AsyncMock(return_value=True))
    actors = {
        "patient": patient_user,
        "patient_profile": patient,
        "doctor": doctor_user,
        "doctor_profile": doctor,
        "responder": responder,
        "admin": admin,
        "department": department,
    }
    actors["tokens"] = {
        key: create_access_token(subject=actors[key].id, claims={"role": actors[key].role})
        for key in ("patient", "doctor", "responder", "admin")
    }
    return actors
