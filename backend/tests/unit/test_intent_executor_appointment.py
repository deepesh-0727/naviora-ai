from datetime import datetime

import pytest
from sqlalchemy import func, select

from app.models.appointment import Appointment
from app.models.doctor import Department, Doctor
from app.models.hospital import StaffSchedule
from app.models.patient import Patient
from app.models.user import User
from app.services.intent_executor import IntentExecutor


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        current = cls(2035, 6, 14, 8, 0)
        return current.replace(tzinfo=tz) if tz else current


async def add_patient(db_session):
    user = User(
        phone="+919811007001",
        email="voice.booking.patient@test.example",
        password_hash="hash",
        role="patient",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(Patient(
        user_id=user.id,
        first_name="Voice",
        last_name="Patient",
        date_of_birth=datetime(1990, 1, 1),
        gender="unknown",
        emergency_contact="",
        emergency_contact_name="",
    ))
    await db_session.flush()
    return user


async def add_doctor(db_session, *, last_name="Sharma", department_name="Cardiology", suffix="1"):
    user = User(
        phone=f"+91981100701{suffix}",
        email=f"voice.booking.doctor{suffix}@test.example",
        password_hash="hash",
        role="doctor",
        is_active=True,
    )
    department = Department(
        name=department_name,
        floor=1,
        building="A",
        wing="North",
        phone="101",
        email=f"voice.booking.department{suffix}@test.example",
    )
    db_session.add_all([user, department])
    await db_session.flush()
    doctor = Doctor(
        user_id=user.id,
        first_name="Maya",
        last_name=last_name,
        specialization="Cardiology",
        department_id=department.id,
        license_number=f"VOICE-BOOKING-{suffix}",
        years_of_experience=8,
        is_available=True,
        max_patients_per_day=10,
        avg_consultation_time=20,
    )
    db_session.add(doctor)
    await db_session.flush()
    return doctor, department


@pytest.mark.asyncio
async def test_appointment_intent_asks_for_missing_doctor(db_session):
    patient_user = await add_patient(db_session)

    result = await IntentExecutor().execute(
        db_session,
        patient_user,
        {"intent": "appointment", "confidence": 0.9, "entities": {}, "specialized_details": {}},
    )

    assert isinstance(result, dict)
    assert result["needs_clarification"] is True
    assert result["clarification_question"] == "Which doctor would you like to see?"


@pytest.mark.asyncio
async def test_appointment_intent_clarifies_duplicate_doctor_names(db_session):
    patient_user = await add_patient(db_session)
    await add_doctor(db_session, department_name="Cardiology", suffix="2")
    await add_doctor(db_session, department_name="Neurology", suffix="3")

    result = await IntentExecutor().execute(
        db_session,
        patient_user,
        {
            "intent": "appointment",
            "confidence": 0.9,
            "entities": {"doctor": "Dr. Maya Sharma"},
            "specialized_details": {},
        },
    )

    assert result["needs_clarification"] is True
    assert len(result["candidates"]) == 2
    assert {candidate.split(" — ")[-1] for candidate in result["candidates"]} == {"Cardiology", "Neurology"}


@pytest.mark.asyncio
async def test_appointment_intent_resolves_available_slot_without_booking(db_session, monkeypatch):
    from app.services import availability_service

    monkeypatch.setattr(availability_service, "datetime", FixedDateTime)
    patient_user = await add_patient(db_session)
    doctor, department = await add_doctor(db_session, suffix="4")
    db_session.add(StaffSchedule(
        staff_id=doctor.user_id,
        date=datetime(2035, 6, 15),
        start_time=datetime(2035, 6, 15, 9),
        end_time=datetime(2035, 6, 15, 10),
        is_available=True,
    ))
    await db_session.flush()

    result = await IntentExecutor().execute(
        db_session,
        patient_user,
        {
            "intent": "appointment",
            "confidence": 0.9,
            "entities": {"doctor": "Maya Sharma"},
            "specialized_details": {"preferred_time": "2035-06-15T09:00:00"},
        },
    )

    assert result["needs_clarification"] is False
    assert result["needs_confirmation"] is True
    assert result["booking_proposal"]["doctor_id"] == doctor.id
    assert result["booking_proposal"]["department_id"] == department.id
    assert result["booking_proposal"]["scheduled_time"] == "2035-06-15T09:00:00"
    assert await db_session.scalar(select(func.count(Appointment.id))) == 0


@pytest.mark.asyncio
async def test_appointment_intent_offers_available_alternatives(db_session, monkeypatch):
    from app.services import availability_service

    monkeypatch.setattr(availability_service, "datetime", FixedDateTime)
    patient_user = await add_patient(db_session)
    doctor, _department = await add_doctor(db_session, suffix="5")
    db_session.add(StaffSchedule(
        staff_id=doctor.user_id,
        date=datetime(2035, 6, 15),
        start_time=datetime(2035, 6, 15, 9),
        end_time=datetime(2035, 6, 15, 10),
        is_available=True,
    ))
    await db_session.flush()

    result = await IntentExecutor().execute(
        db_session,
        patient_user,
        {
            "intent": "appointment",
            "confidence": 0.9,
            "entities": {"doctor": "Maya Sharma"},
            "specialized_details": {"preferred_time": "2035-06-15T09:15:00"},
        },
    )

    assert result["needs_clarification"] is True
    assert "slot is taken or unavailable" in result["clarification_question"]
    assert result["alternatives"][:2] == ["2035-06-15T09:00:00", "2035-06-15T09:20:00"]
