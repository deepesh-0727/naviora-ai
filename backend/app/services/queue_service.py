import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.queue import QueueEntry
from app.services.availability_service import database_datetime
from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)


class QueueService:
    @staticmethod
    def _queue_key(doctor_id: int) -> str:
        return f"queue:doctor:{doctor_id}"

    @staticmethod
    def _redis() -> Redis:
        return Redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def _members(self, db: AsyncSession, redis: Redis, doctor_id: int) -> list[str]:
        key = self._queue_key(doctor_id)
        members = await redis.zrange(key, 0, -1)
        if members:
            return members
        entries_result = await db.execute(
            select(QueueEntry)
            .where(
                QueueEntry.doctor_id == doctor_id,
                QueueEntry.status.in_(["queued", "treating"]),
            )
            .order_by(QueueEntry.entered_at.asc(), QueueEntry.id.asc())
        )
        entries = entries_result.scalars().all()
        if entries:
            await redis.zadd(
                key,
                {
                    str(entry.appointment_id): database_datetime(entry.entered_at).timestamp()
                    for entry in entries
                },
            )
            members = await redis.zrange(key, 0, -1)
        return members

    async def calculate_wait_time(self, db: AsyncSession, doctor_id: int, position: int) -> int:
        result = await db.execute(select(Doctor.avg_consultation_time).where(Doctor.id == doctor_id))
        average_minutes = result.scalar_one_or_none()
        if average_minutes is None:
            raise HTTPException(status_code=404, detail="Doctor not found.")
        return max(position, 0) * max(average_minutes, 1)

    async def add_to_queue(self, db: AsyncSession, appointment_id: int, doctor_id: int) -> dict[str, int]:
        appointment_result = await db.execute(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.doctor_id == doctor_id,
                Appointment.status.in_(["check_in", "treating"]),
            )
        )
        appointment = appointment_result.scalar_one_or_none()
        if appointment is None:
            raise HTTPException(status_code=404, detail="Active appointment not found for this doctor.")

        redis = self._redis()
        added = False
        try:
            key = self._queue_key(doctor_id)
            score = database_datetime(appointment.actual_time or appointment.scheduled_time).timestamp()
            added = bool(await redis.zadd(key, {str(appointment_id): score}, nx=True))
            rank = await redis.zrank(key, str(appointment_id))
            if rank is None:
                raise HTTPException(status_code=503, detail="Unable to determine queue position.")
            position = int(rank) + 1
            appointment.queue_position = position
            appointment.wait_time_minutes = await self.calculate_wait_time(db, doctor_id, position)
            entry_result = await db.execute(
                select(QueueEntry).where(QueueEntry.appointment_id == appointment_id)
            )
            entry = entry_result.scalar_one_or_none()
            if entry is None:
                entry = QueueEntry(
                    appointment_id=appointment_id,
                    doctor_id=doctor_id,
                    position=position,
                    status="treating" if appointment.status == "treating" else "queued",
                    entered_at=appointment.actual_time or datetime.now(timezone.utc).replace(tzinfo=None),
                )
                db.add(entry)
            else:
                entry.position = position
                entry.status = "treating" if appointment.status == "treating" else "queued"
            await db.commit()
            await db.refresh(appointment)
            await self.notify_queue_updates(db, doctor_id, redis_client=redis)
            return {"position": position, "estimated_wait_minutes": appointment.wait_time_minutes}
        except RedisError as exc:
            await db.rollback()
            if added:
                try:
                    await redis.zrem(self._queue_key(doctor_id), str(appointment_id))
                except RedisError:
                    logger.exception("Failed to roll back Redis queue membership")
            raise HTTPException(status_code=503, detail="Queue service is unavailable.") from exc
        finally:
            await redis.aclose()

    async def get_queue_status(self, db: AsyncSession, doctor_id: int) -> list[dict[str, object]]:
        redis = self._redis()
        try:
            members = await self._members(db, redis, doctor_id)
            if not members:
                return []
            appointment_ids = [int(member) for member in members]
            result = await db.execute(
                select(Appointment).where(
                    Appointment.id.in_(appointment_ids),
                    Appointment.doctor_id == doctor_id,
                    Appointment.status.in_(["check_in", "treating"]),
                )
            )
            appointments = {item.id: item for item in result.scalars().all()}
            stale_members = [member for member in members if int(member) not in appointments]
            if stale_members:
                await redis.zrem(self._queue_key(doctor_id), *stale_members)
            queue: list[dict[str, object]] = []
            for member in members:
                appointment = appointments.get(int(member))
                if appointment is None:
                    continue
                position = len(queue) + 1
                appointment.queue_position = position
                appointment.wait_time_minutes = await self.calculate_wait_time(db, doctor_id, position)
                entry_result = await db.execute(
                    select(QueueEntry).where(QueueEntry.appointment_id == appointment.id)
                )
                entry = entry_result.scalar_one_or_none()
                if entry is not None:
                    entry.position = position
                queue.append({
                    "id": appointment.id,
                    "appointment_id": appointment.id,
                    "patient_id": appointment.patient_id,
                    "doctor_id": appointment.doctor_id,
                    "position": position,
                    "status": appointment.status,
                    "priority": appointment.priority,
                    "scheduled_time": appointment.scheduled_time,
                    "estimated_wait_minutes": appointment.wait_time_minutes,
                })
            await db.commit()
            return queue
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="Queue service is unavailable.") from exc
        finally:
            await redis.aclose()

    async def mark_served(self, db: AsyncSession, appointment_id: int, doctor_id: int) -> bool:
        result = await db.execute(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.doctor_id == doctor_id,
                Appointment.status.in_(["check_in", "treating"]),
            )
        )
        appointment = result.scalar_one_or_none()
        if appointment is None:
            return False

        redis = self._redis()
        try:
            await redis.zrem(self._queue_key(doctor_id), str(appointment_id))
            appointment.status = "completed"
            appointment.queue_position = 0
            appointment.actual_time = appointment.actual_time or datetime.now(timezone.utc).replace(tzinfo=None)
            entry_result = await db.execute(
                select(QueueEntry).where(QueueEntry.appointment_id == appointment_id)
            )
            entry = entry_result.scalar_one_or_none()
            if entry is not None:
                entry.status = "served"
                entry.position = 0
                entry.served_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()
            await self.notify_queue_updates(db, doctor_id, redis_client=redis)
            return True
        except RedisError as exc:
            await db.rollback()
            raise HTTPException(status_code=503, detail="Queue service is unavailable.") from exc
        finally:
            await redis.aclose()

    async def join_queue(self, db: AsyncSession, appointment_id: int) -> Optional[Appointment]:
        result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
        appointment = result.scalar_one_or_none()
        if appointment is None or appointment.status != "scheduled":
            return None

        appointment.status = "check_in"
        appointment.actual_time = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.flush()
        try:
            await self.add_to_queue(db, appointment.id, appointment.doctor_id)
        except Exception:
            await db.rollback()
            raise
        await db.refresh(appointment)
        return appointment

    async def get_next_patient(self, db: AsyncSession, doctor_id: int) -> Optional[Appointment]:
        treating_result = await db.execute(
            select(Appointment.id).where(
                Appointment.doctor_id == doctor_id,
                Appointment.status == "treating",
            ).limit(1)
        )
        treating_id = treating_result.scalar_one_or_none()
        if treating_id is not None:
            await self.mark_served(db, treating_id, doctor_id)

        redis = self._redis()
        try:
            members = await self._members(db, redis, doctor_id)
            if not members:
                return None
            result = await db.execute(
                select(Appointment)
                .options(selectinload(Appointment.patient))
                .where(
                    Appointment.id.in_([int(member) for member in members]),
                    Appointment.doctor_id == doctor_id,
                    Appointment.status == "check_in",
                )
            )
            appointments = {item.id: item for item in result.scalars().all()}
            next_appointment = next((appointments[int(member)] for member in members if int(member) in appointments), None)
            if next_appointment is None:
                return None
            next_appointment.status = "treating"
            entry_result = await db.execute(
                select(QueueEntry).where(QueueEntry.appointment_id == next_appointment.id)
            )
            entry = entry_result.scalar_one_or_none()
            if entry is not None:
                entry.status = "treating"
            await db.commit()
            await db.refresh(next_appointment)
            await ws_manager.send_personal_message(
                {"type": "queue_alert", "message": "It is your turn. Please proceed to the doctor's cabin."},
                str(next_appointment.patient.user_id),
            )
            await self.notify_queue_updates(db, doctor_id, redis_client=redis)
            return next_appointment
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="Queue service is unavailable.") from exc
        finally:
            await redis.aclose()

    async def notify_queue_updates(self, db: AsyncSession, doctor_id: int, redis_client: Optional[Redis] = None) -> None:
        redis = redis_client or self._redis()
        close_client = redis_client is None
        try:
            members = await self._members(db, redis, doctor_id)
            if not members:
                return
            result = await db.execute(
                select(Appointment)
                .options(selectinload(Appointment.patient))
                .where(Appointment.id.in_([int(member) for member in members]))
            )
            appointments = {item.id: item for item in result.scalars().all()}
            for position, member in enumerate(members, start=1):
                appointment = appointments.get(int(member))
                if appointment is None:
                    continue
                wait = await self.calculate_wait_time(db, doctor_id, position)
                appointment.queue_position = position
                appointment.wait_time_minutes = wait
                entry_result = await db.execute(
                    select(QueueEntry).where(QueueEntry.appointment_id == appointment.id)
                )
                entry = entry_result.scalar_one_or_none()
                if entry is not None:
                    entry.position = position
                    entry.status = "treating" if appointment.status == "treating" else "queued"
                await ws_manager.send_personal_message(
                    {"type": "queue_update", "position": position, "estimated_wait": wait},
                    str(appointment.patient.user_id),
                )
            await db.commit()
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="Queue service is unavailable.") from exc
        finally:
            if close_client:
                await redis.aclose()


queue_service = QueueService()
