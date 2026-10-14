from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.hospital import StaffSchedule


def database_datetime(value: datetime) -> datetime:
    """Normalize timestamps to the UTC-naive format used by current DB columns."""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


async def get_available_slots(db: AsyncSession, doctor: Doctor, for_date: date) -> list[str]:
    if not doctor.is_available:
        return []
    day_start = datetime.combine(for_date, time.min)
    day_end = datetime.combine(for_date, time.max)
    schedule_result = await db.execute(
        select(StaffSchedule)
        .where(
            StaffSchedule.staff_id == doctor.user_id,
            StaffSchedule.date == day_start,
            StaffSchedule.is_available.is_(True),
        )
        .order_by(StaffSchedule.start_time.asc())
    )
    shifts = schedule_result.scalars().all()
    if not shifts:
        return []

    booked_result = await db.execute(
        select(Appointment.scheduled_time).where(
            Appointment.doctor_id == doctor.id,
            Appointment.scheduled_time >= day_start,
            Appointment.scheduled_time <= day_end,
            Appointment.status.in_(["scheduled", "check_in", "treating"]),
        )
    )
    booked = {database_datetime(value) for value in booked_result.scalars().all()}
    day_count_result = await db.execute(
        select(Appointment.id).where(
            Appointment.doctor_id == doctor.id,
            Appointment.scheduled_time >= day_start,
            Appointment.scheduled_time <= day_end,
            Appointment.status.in_(["scheduled", "check_in", "treating"]),
        )
    )
    remaining_capacity = max(doctor.max_patients_per_day - len(day_count_result.all()), 0)
    if remaining_capacity == 0:
        return []

    duration = timedelta(minutes=max(doctor.avg_consultation_time, 1))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    slots: list[str] = []
    for shift in shifts:
        cursor = database_datetime(shift.start_time)
        shift_end = database_datetime(shift.end_time)
        while cursor + duration <= shift_end and len(slots) < remaining_capacity:
            if cursor >= now and cursor not in booked:
                slots.append(cursor.isoformat())
            cursor += duration
    return slots
