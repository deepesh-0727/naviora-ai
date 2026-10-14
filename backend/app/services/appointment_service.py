from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.appointment import Appointment

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
        raise HTTPException(
            status_code=501,
            detail="Smart booking is unavailable; use the date-based appointment availability API.",
        )

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
