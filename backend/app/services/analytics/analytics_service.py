import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.appointment import Appointment
from app.models.emergency import EmergencyCase
from app.models.hospital import Feedback

logger = logging.getLogger(__name__)

class AnalyticsService:
    async def get_hospital_kpis(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Calculate key performance indicators for the hospital.
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. Total Appointments Today
        count_result = await db.execute(
            select(func.count(Appointment.id)).filter(Appointment.created_at >= today_start)
        )
        total_today = count_result.scalar() or 0

        # 2. Avg Wait Time (Completed Appointments)
        wait_result = await db.execute(
            select(func.avg(Appointment.wait_time_minutes))
            .filter(Appointment.status == "completed", Appointment.updated_at >= today_start)
        )
        avg_wait = wait_result.scalar() or 0.0

        # 3. Active Emergency Cases
        emergency_result = await db.execute(
            select(func.count(EmergencyCase.id)).filter(EmergencyCase.status != "resolved")
        )
        active_emergencies = emergency_result.scalar() or 0

        # 4. Patient Satisfaction (Feedback)
        feedback_result = await db.execute(
            select(func.avg(Feedback.rating)).filter(Feedback.created_at >= today_start - timedelta(days=7))
        )
        avg_rating = feedback_result.scalar() or 0.0

        return {
            "total_appointments_today": total_today,
            "avg_wait_time_minutes": round(float(avg_wait), 2),
            "active_emergencies": active_emergencies,
            "patient_satisfaction_score": round(float(avg_rating), 2)
        }

    async def get_department_load(self, db: AsyncSession) -> List[Dict[str, Any]]:
        # Logic to aggregate appointments by department
        return []

analytics_service = AnalyticsService()
