"""Pilot KPIs computed from persisted application records."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.emergency import EmergencyCase
from app.models.hospital import Feedback
from app.models.queue import QueueEntry
from app.models.user import User
from app.models.voice_interaction import VoiceInteraction

router = APIRouter()
ADMIN_ROLES = ["admin", "super_admin"]


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


@router.get("/metrics")
async def get_pilot_metrics(
    start: datetime | None = None,
    end: datetime | None = None,
    _admin: User = Depends(deps.check_role(ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Return pilot KPIs for [start, end); default to the preceding 30 days."""
    period_end = _utc_naive(end) if end else datetime.now(timezone.utc).replace(tzinfo=None)
    period_start = _utc_naive(start) if start else period_end - timedelta(days=30)
    if period_start >= period_end:
        raise HTTPException(status_code=422, detail="start must be earlier than end.")

    # QueueEntry timestamps represent actual time in the queue. Appointment.actual_time
    # is written at completion and therefore is not a valid wait-start timestamp.
    wait_rows = await db.execute(
        select(QueueEntry.entered_at, QueueEntry.served_at).where(
            QueueEntry.served_at >= period_start,
            QueueEntry.served_at < period_end,
            QueueEntry.entered_at.is_not(None),
        )
    )
    wait_minutes = [
        (served_at - entered_at).total_seconds() / 60
        for entered_at, served_at in wait_rows.all()
        if served_at is not None and entered_at is not None and served_at >= entered_at
    ]

    emergency_rows = await db.execute(
        select(EmergencyCase.created_at, EmergencyCase.arrival_time).where(
            EmergencyCase.arrival_time >= period_start,
            EmergencyCase.arrival_time < period_end,
            EmergencyCase.created_at.is_not(None),
        )
    )
    response_seconds = [
        (arrival_time - created_at).total_seconds()
        for created_at, arrival_time in emergency_rows.all()
        if created_at is not None and arrival_time is not None and arrival_time >= created_at
    ]
    unresolved_emergencies = await db.scalar(
        select(func.count(EmergencyCase.id)).where(
            EmergencyCase.created_at >= period_start,
            EmergencyCase.created_at < period_end,
            EmergencyCase.arrival_time.is_(None),
        )
    )

    no_show_counts = await db.execute(
        select(
            func.count(Appointment.id),
            func.count(Appointment.id).filter(Appointment.status == "no_show"),
        ).where(
            Appointment.scheduled_time >= period_start,
            Appointment.scheduled_time < period_end,
            Appointment.scheduled_time < datetime.now(timezone.utc).replace(tzinfo=None),
            Appointment.status != "cancelled",
        )
    )
    appointment_total, no_shows = no_show_counts.one()
    appointment_total = int(appointment_total or 0)
    no_shows = int(no_shows or 0)

    voice_counts = await db.execute(
        select(func.count(VoiceInteraction.id), func.avg(VoiceInteraction.confidence)).where(
            VoiceInteraction.created_at >= period_start,
            VoiceInteraction.created_at < period_end,
        )
    )
    voice_total, average_confidence = voice_counts.one()
    reviewed_counts = await db.execute(
        select(
            func.count(VoiceInteraction.id),
            func.count(VoiceInteraction.id).filter(VoiceInteraction.reviewed_correct.is_(True)),
        ).where(
            VoiceInteraction.created_at >= period_start,
            VoiceInteraction.created_at < period_end,
            VoiceInteraction.reviewed_correct.is_not(None),
        )
    )
    reviewed_total, reviewed_correct = reviewed_counts.one()
    reviewed_total = int(reviewed_total or 0)
    reviewed_correct = int(reviewed_correct or 0)

    nps_counts = await db.execute(
        select(
            func.count(Feedback.id),
            func.count(Feedback.id).filter(Feedback.nps_score >= 9),
            func.count(Feedback.id).filter(Feedback.nps_score <= 6),
        ).where(
            Feedback.created_at >= period_start,
            Feedback.created_at < period_end,
            Feedback.nps_score.is_not(None),
        )
    )
    nps_total, promoters, detractors = (int(value or 0) for value in nps_counts.one())

    satisfaction_counts = await db.execute(
        select(
            func.count(Feedback.id),
            func.count(Feedback.id).filter(Feedback.rating >= 4),
        ).where(
            Feedback.created_at >= period_start,
            Feedback.created_at < period_end,
        )
    )
    satisfaction_total, favorable_ratings = (
        int(value or 0) for value in satisfaction_counts.one()
    )

    active_counts = await db.execute(
        select(
            func.count(User.id).filter(User.last_login >= period_end - timedelta(days=1)),
            func.count(User.id).filter(User.last_login >= period_end - timedelta(days=7)),
        ).where(
            User.is_active.is_(True),
            User.role.in_(["doctor", "staff"]),
            User.last_login < period_end,
        )
    )
    active_daily, active_weekly = (int(value or 0) for value in active_counts.one())

    return {
        "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
        "wait_time": {
            "avg_minutes": round(sum(wait_minutes) / len(wait_minutes), 2) if wait_minutes else None,
            "p50": round(_percentile(wait_minutes, 0.5), 2) if wait_minutes else None,
            "p95": round(_percentile(wait_minutes, 0.95), 2) if wait_minutes else None,
            "sample_size": len(wait_minutes),
        },
        "emergency_response": {
            "avg_seconds": round(sum(response_seconds) / len(response_seconds), 2)
            if response_seconds else None,
            "sample_size": len(response_seconds),
            "unresolved_created_in_period": int(unresolved_emergencies or 0),
        },
        "no_show_rate": {
            "rate": round(no_shows / appointment_total, 4) if appointment_total else None,
            "total": appointment_total,
            "no_shows": no_shows,
        },
        "voice_intents": {
            "total": int(voice_total or 0),
            "avg_confidence": round(float(average_confidence), 4)
            if average_confidence is not None else None,
            "reviewed_accuracy": round(reviewed_correct / reviewed_total, 4)
            if reviewed_total else None,
            "reviewed_sample_size": reviewed_total,
        },
        "patient_satisfaction": {
            "nps": round(100 * (promoters - detractors) / nps_total, 2) if nps_total else None,
            "nps_responses": nps_total,
            "favorable_rating_share": round(favorable_ratings / satisfaction_total, 4)
            if satisfaction_total else None,
            "rating_responses": satisfaction_total,
        },
        "active_staff": {"daily": active_daily, "weekly": active_weekly},
        "uptime": {"last_30d": None, "source": "manual_uptimerobot_review"},
    }
