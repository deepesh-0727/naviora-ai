"""Durable, database-backed dispatch for post-visit feedback reminders."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.appointment import Appointment
from app.models.communication import Notification
from app.models.feedback_reminder import FeedbackReminder
from app.models.patient import Patient
from app.services.notification.push_service import push_service

logger = logging.getLogger(__name__)
POLL_SECONDS = 30


async def schedule_feedback_reminder(db: AsyncSession, appointment: Appointment) -> None:
    existing = await db.scalar(
        select(FeedbackReminder.id).where(FeedbackReminder.appointment_id == appointment.id)
    )
    if existing is None:
        db.add(
            FeedbackReminder(
                appointment_id=appointment.id,
                patient_id=appointment.patient_id,
                scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1),
                status="pending",
            )
        )


async def dispatch_due_feedback_reminders(session_factory: async_sessionmaker[AsyncSession]) -> int:
    sent_count = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with session_factory() as db:
        result = await db.execute(
            select(FeedbackReminder)
            .where(
                or_(
                    FeedbackReminder.status == "pending",
                    (FeedbackReminder.status == "processing")
                    & (FeedbackReminder.processing_at <= now - timedelta(minutes=5)),
                ),
                FeedbackReminder.scheduled_at <= datetime.now(timezone.utc).replace(tzinfo=None),
            )
            .order_by(FeedbackReminder.scheduled_at)
            .limit(25)
            .with_for_update(skip_locked=True)
        )
        reminders = result.scalars().all()
        for reminder in reminders:
            reminder.status = "processing"
            reminder.processing_at = now
        await db.commit()

    for reminder_id in [item.id for item in reminders]:
        async with session_factory() as db:
            reminder = await db.get(FeedbackReminder, reminder_id)
            if reminder is None or reminder.status != "processing":
                continue
            patient = await db.get(Patient, reminder.patient_id)
            appointment = await db.get(Appointment, reminder.appointment_id)
            if patient is None or appointment is None or appointment.status != "completed":
                reminder.status = "cancelled"
                await db.commit()
                continue
            user_id = patient.user_id
            data = {"type": "feedback_request", "appointment_id": str(appointment.id)}
            prior = await db.execute(
                select(Notification.id).where(
                    Notification.user_id == user_id,
                    Notification.type == "push",
                    Notification.data["appointment_id"].as_string() == str(appointment.id),
                ).limit(1)
            )
            if prior.scalar_one_or_none() is None:
                db.add(
                    Notification(
                        user_id=user_id,
                        type="push",
                        channel="push",
                        title="How was your visit?",
                        message="Share feedback about your recent visit to help improve your experience.",
                        data=data,
                    )
                )
                await db.commit()
            try:
                delivered = await push_service.send_push_notification_to_user(
                    db,
                    user_id,
                    "How was your visit?",
                    "Share feedback about your recent visit to help improve your experience.",
                    data,
                )
            except Exception as exc:
                logger.exception("Feedback reminder push failed for reminder %s", reminder.id)
                delivered = False
                error = str(exc)
            else:
                error = None if delivered else "No registered device accepted the push notification."

            reminder = await db.get(FeedbackReminder, reminder_id)
            if reminder is None:
                continue
            reminder.attempts += 1
            reminder.processing_at = None
            if delivered:
                reminder.status = "sent"
                reminder.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
                reminder.last_error = None
                sent_count += 1
            elif reminder.attempts >= 3:
                reminder.status = "failed"
                reminder.last_error = error[:500] if error else "Push delivery failed."
            else:
                reminder.status = "pending"
                reminder.scheduled_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)
                reminder.last_error = error[:500] if error else "Push delivery failed."
            await db.commit()
    return sent_count


async def feedback_scheduler_loop(
    session_factory: async_sessionmaker[AsyncSession],
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        try:
            await dispatch_due_feedback_reminders(session_factory)
        except Exception:
            logger.exception("Feedback reminder scheduler pass failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=POLL_SECONDS)
        except TimeoutError:
            pass
