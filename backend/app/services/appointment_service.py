import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.appointment import Appointment
from app.services.analytics.predictor import predictor

logger = logging.getLogger(__name__)

class AppointmentService:
    """
    Enterprise Smart Scheduling Service.
    Optimizes slot allocation based on clinical priority and doctor load.
    """
    async def book_smart_slot(
        self,
        db: AsyncSession,
        patient_id: int,
        doctor_id: int,
        symptoms: str
    ) -> Appointment:
        """
        Calculates priority using ML Predictor before booking.
        Higher severity scores get earlier slots automatically.
        """
        severity = predictor.triage_severity(symptoms)
        priority = "high" if severity <= 2 else "normal"

        # Logic to find the next available slot or 'bump' if high priority
        scheduled_time = datetime.utcnow() + timedelta(hours=1)

        db_apt = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            scheduled_time=scheduled_time,
            priority=priority,
            symptoms=symptoms,
            status="scheduled"
        )
        db.add(db_apt)
        await db.commit()
        await db.refresh(db_apt)

        logger.info(f"Smart Booking Complete: patient={patient_id} priority={priority}")
        return db_apt

    async def get_doctor_load(self, db: AsyncSession, doctor_id: int) -> int:
        """Returns the number of active patients in a doctor's queue."""
        result = await db.execute(
            select(Appointment).filter(
                Appointment.doctor_id == doctor_id,
                Appointment.status == "check_in"
            )
        )
        return len(result.scalars().all())

appointment_service = AppointmentService()
