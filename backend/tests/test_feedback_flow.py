from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models.appointment import Appointment
from app.models.communication import Notification
from app.models.feedback_reminder import FeedbackReminder
from app.models.hospital import Feedback
from app.models.patient import Patient
from app.models.user import User
from app.services.feedback_scheduler import dispatch_due_feedback_reminders, schedule_feedback_reminder
from app.services.notification.push_service import push_service


async def _completed_appointment(db_session):
    user = User(
        phone="+919811007001",
        email="feedback.flow.patient@test.example",
        password_hash="hash",
        role="patient",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    patient = Patient(
        user_id=user.id,
        first_name="Flow",
        last_name="Patient",
        date_of_birth=datetime(1990, 1, 1),
        gender="unknown",
        emergency_contact="",
        emergency_contact_name="",
    )
    db_session.add(patient)
    await db_session.flush()
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=1,
        department_id=1,
        scheduled_time=datetime.now(timezone.utc).replace(tzinfo=None),
        status="completed",
    )
    db_session.add(appointment)
    await db_session.commit()
    return appointment, patient


@pytest.mark.asyncio
async def test_completion_schedules_feedback_push_one_hour_later(db_session):
    appointment, _ = await _completed_appointment(db_session)
    before = datetime.now(timezone.utc).replace(tzinfo=None)

    await schedule_feedback_reminder(db_session, appointment)
    await db_session.commit()

    reminder = await db_session.scalar(
        select(FeedbackReminder).where(
            FeedbackReminder.appointment_id == appointment.id
        )
    )
    assert reminder.status == "pending"
    assert before + timedelta(hours=1) <= reminder.scheduled_at <= before + timedelta(hours=1, seconds=2)


@pytest.mark.asyncio
async def test_due_reminder_creates_notification_and_sends_push(db_session, test_session_factory, monkeypatch):
    appointment, patient = await _completed_appointment(db_session)
    reminder = FeedbackReminder(
        appointment_id=appointment.id,
        patient_id=patient.id,
        scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1),
        status="pending",
    )
    db_session.add(reminder)
    await db_session.commit()
    send_push = AsyncMock(return_value=True)
    monkeypatch.setattr(push_service, "send_push_notification_to_user", send_push)

    assert await dispatch_due_feedback_reminders(test_session_factory) == 1

    await db_session.refresh(reminder)
    assert reminder.status == "sent"
    assert reminder.attempts == 1
    assert reminder.sent_at is not None
    notification = await db_session.scalar(
        select(Notification).where(Notification.user_id == patient.user_id)
    )
    assert notification.data == {"type": "feedback_request", "appointment_id": str(appointment.id)}
    send_push.assert_awaited_once()


@pytest.mark.asyncio
async def test_feedback_submission_persists_real_nps_and_help_answer(async_client, db_session):
    from app.core.security import create_access_token

    appointment, patient = await _completed_appointment(db_session)
    token = create_access_token(subject=patient.user_id, claims={"role": "patient"})
    response = await async_client.post(
        "/api/v1/feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "appointment_id": appointment.id,
            "rating": 5,
            "nps_score": 10,
            "comments": "Did Naviora AI help: yes\nSuggested improvement: clearer queue time",
        },
    )
    assert response.status_code == 201, response.text
    record = await db_session.get(Feedback, response.json()["id"])
    assert record.nps_score == 10
    assert "Did Naviora AI help: yes" in record.comments
