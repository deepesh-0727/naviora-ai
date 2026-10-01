import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, func

from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)

class QueueService:
    async def join_queue(self, db: AsyncSession, appointment_id: int) -> Optional[Appointment]:
        """
        Patient checks in and joins the live queue for their doctor.
        """
        result = await db.execute(select(Appointment).filter(Appointment.id == appointment_id))
        appointment = result.scalars().first()

        if not appointment or appointment.status != "scheduled":
            return None

        # Calculate next position in queue for this doctor today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        pos_result = await db.execute(
            select(func.max(Appointment.queue_position))
            .filter(
                Appointment.doctor_id == appointment.doctor_id,
                Appointment.status.in_(["check_in", "treating"]),
                Appointment.created_at >= today_start
            )
        )
        max_pos = pos_result.scalar() or 0

        appointment.status = "check_in"
        appointment.queue_position = max_pos + 1
        appointment.actual_time = datetime.utcnow()

        await db.commit()
        await db.refresh(appointment)

        # Notify patient of their position
        await ws_manager.send_personal_message(
            {
                "type": "queue_update",
                "status": "checked_in",
                "position": appointment.queue_position,
                "estimated_wait": await self.calculate_wait_time(db, appointment.doctor_id, appointment.queue_position)
            },
            str(appointment.patient.user_id)
        )

        return appointment

    async def get_next_patient(self, db: AsyncSession, doctor_id: int) -> Optional[Appointment]:
        """
        Doctor calls the next patient in their queue.
        """
        # Complete currently 'treating' appointment if any
        await db.execute(
            update(Appointment)
            .filter(Appointment.doctor_id == doctor_id, Appointment.status == "treating")
            .values(status="completed", updated_at=datetime.utcnow())
        )

        # Find patient with lowest queue_position > 0 who is 'check_in'
        result = await db.execute(
            select(Appointment)
            .filter(Appointment.doctor_id == doctor_id, Appointment.status == "check_in")
            .order_by(Appointment.queue_position.asc())
            .limit(1)
        )
        next_app = result.scalars().first()

        if next_app:
            next_app.status = "treating"
            await db.commit()
            await db.refresh(next_app)

            # Notify the patient being called
            await ws_manager.send_personal_message(
                {"type": "queue_alert", "message": "It is your turn! Please proceed to the doctor's cabin."},
                str(next_app.patient.user_id)
            )

            # Broadcast update to the rest of the queue
            await self.notify_queue_updates(db, doctor_id)

        return next_app

    async def calculate_wait_time(self, db: AsyncSession, doctor_id: int, position: int) -> int:
        """
        Estimate wait time in minutes based on doctor's avg consultation time.
        """
        result = await db.execute(select(Doctor).filter(Doctor.id == doctor_id))
        doctor = result.scalars().first()

        # Default to 15 mins per patient if not specified or found
        avg_time = 15
        if doctor and hasattr(doctor, 'avg_consultation_time'):
            avg_time = doctor.avg_consultation_time or 15

        return position * avg_time

    async def notify_queue_updates(self, db: AsyncSession, doctor_id: int):
        """
        Broadcast position updates to all checked-in patients for a specific doctor.
        """
        result = await db.execute(
            select(Appointment)
            .filter(Appointment.doctor_id == doctor_id, Appointment.status == "check_in")
            .order_by(Appointment.queue_position.asc())
        )
        queue = result.scalars().all()

        for i, app in enumerate(queue):
            # Recalculate relative position
            relative_pos = i + 1
            await ws_manager.send_personal_message(
                {
                    "type": "queue_update",
                    "position": relative_pos,
                    "estimated_wait": await self.calculate_wait_time(db, doctor_id, relative_pos)
                },
                str(app.patient.user_id)
            )

queue_service = QueueService()
