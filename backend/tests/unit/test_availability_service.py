from datetime import date, datetime

import pytest

from app.models.doctor import Department, Doctor
from app.models.hospital import StaffSchedule
from app.models.user import User
from app.services import availability_service
from app.services.availability_service import get_available_slots


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2029, 12, 1, 0, 0)
        return value.replace(tzinfo=tz) if tz else value


@pytest.fixture
async def scheduled_doctor(db_session, monkeypatch):
    monkeypatch.setattr(availability_service, "datetime", FixedDateTime)
    user = User(phone="+919800000401", email="availability@tests.example", password_hash="hash", role="doctor")
    department = Department(name="Availability Tests", floor=1, building="A", wing="West", phone="101", email="availability@tests.example")
    db_session.add_all([user, department])
    await db_session.flush()
    doctor = Doctor(user_id=user.id, first_name="Mira", last_name="Sen", specialization="General", department_id=department.id, license_number="AVAIL-TEST-1", years_of_experience=8, avg_consultation_time=30, max_patients_per_day=4)
    db_session.add(doctor)
    await db_session.flush()
    shift_date = datetime(2030, 1, 2)
    db_session.add(StaffSchedule(staff_id=user.id, date=shift_date, start_time=datetime(2030, 1, 2, 9), end_time=datetime(2030, 1, 2, 11), is_available=True))
    await db_session.commit()
    return doctor


@pytest.mark.asyncio
async def test_availability_returns_future_unbooked_slots_for_real_schedule(db_session, scheduled_doctor):
    slots = await get_available_slots(db_session, scheduled_doctor, date(2030, 1, 2))

    assert slots == ["2030-01-02T09:00:00", "2030-01-02T09:30:00", "2030-01-02T10:00:00", "2030-01-02T10:30:00"]


@pytest.mark.asyncio
async def test_availability_excludes_real_booked_slot_and_respects_capacity(db_session, scheduled_doctor):
    from app.models.appointment import Appointment
    from app.models.patient import Patient

    patient_user = User(phone="+919800000402", email="availability-patient@tests.example", password_hash="hash", role="patient")
    db_session.add(patient_user)
    await db_session.flush()
    patient = Patient(user_id=patient_user.id, first_name="Test", last_name="Patient", date_of_birth=datetime(1991, 2, 3), gender="unknown", emergency_contact="", emergency_contact_name="")
    db_session.add(patient)
    await db_session.flush()
    db_session.add(Appointment(patient_id=patient.id, doctor_id=scheduled_doctor.id, department_id=scheduled_doctor.department_id, scheduled_time=datetime(2030, 1, 2, 9, 30), status="scheduled"))
    scheduled_doctor.max_patients_per_day = 2
    await db_session.commit()

    slots = await get_available_slots(db_session, scheduled_doctor, date(2030, 1, 2))

    assert slots == ["2030-01-02T09:00:00"]


@pytest.mark.asyncio
async def test_availability_returns_no_slots_for_doctor_on_leave(db_session, scheduled_doctor):
    scheduled_doctor.is_available = False

    slots = await get_available_slots(db_session, scheduled_doctor, date(2030, 1, 2))

    assert slots == []
