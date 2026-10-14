from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.user import User
from app.services.emergency_service import emergency_service


class IntentExecutor:
    """Execute only intents backed by a persisted service operation."""

    async def execute(self, db: AsyncSession, user: User, analysis: dict[str, Any]) -> str:
        intent = analysis.get("intent")
        if analysis.get("needs_clarification") or float(analysis.get("confidence") or 0) < 0.6:
            return "I could not identify the request with enough confidence. Please rephrase or provide more details."
        details = analysis.get("specialized_details") or {}
        if intent != "emergency":
            raise HTTPException(
                status_code=501,
                detail=f"The {intent or 'requested'} voice action is not available yet.",
            )

        patient_result = await db.execute(select(Patient.id).where(Patient.user_id == user.id))
        patient_id = patient_result.scalar_one_or_none()
        location = details.get("location") or details.get("location_clues")
        description = details.get("emergency_type") or details.get("description")
        if patient_id is None:
            raise HTTPException(status_code=403, detail="Emergency voice requests require a patient account.")
        if not isinstance(location, str) or not location.strip():
            return "Please share your current location so I can submit the emergency request."

        result = await emergency_service.trigger_sos(
            db,
            patient_id,
            location.strip(),
            description.strip() if isinstance(description, str) else "",
        )
        return f"Emergency request {result['emergency_id']} was recorded."


intent_executor = IntentExecutor()
