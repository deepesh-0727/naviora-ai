from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException

from app.models.doctor import Doctor


class Predictor:
    """Data-backed operational estimates; clinical triage requires a validated model."""

    async def predict_wait_time(
        self,
        db: AsyncSession,
        doctor_id: int,
        position: int,
    ) -> int:
        if position < 1:
            raise HTTPException(status_code=422, detail="Queue position must be positive.")
        result = await db.execute(
            select(Doctor.avg_consultation_time).where(Doctor.id == doctor_id)
        )
        average_minutes = result.scalar_one_or_none()
        if average_minutes is None:
            raise HTTPException(status_code=404, detail="Doctor not found.")
        return position * max(average_minutes, 1)

    def triage_severity(self, symptoms: str, vitals: dict[str, float] | None = None) -> int:
        raise HTTPException(
            status_code=501,
            detail="Clinical triage is unavailable until a validated model is configured.",
        )


predictor = Predictor()
