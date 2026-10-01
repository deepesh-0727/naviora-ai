from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.hospital import Feedback
from app.models.patient import Patient
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
@router.post(
    "/patients/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_feedback(
    feedback: FeedbackCreate,
    current_user=Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    patient_result = await db.execute(
        select(Patient).where(Patient.user_id == current_user.id)
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found.")

    appointment_result = await db.execute(
        select(Appointment).where(
            Appointment.id == feedback.appointment_id,
            Appointment.patient_id == patient.id,
        )
    )
    appointment = appointment_result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    if appointment.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Feedback can only be submitted for a completed appointment.",
        )

    existing_result = await db.execute(
        select(Feedback.id)
        .where(
            Feedback.appointment_id == appointment.id,
            Feedback.patient_id == patient.id,
        )
        .limit(1)
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail="Feedback has already been submitted for this appointment.",
        )

    record = Feedback(
        appointment_id=appointment.id,
        patient_id=patient.id,
        rating=feedback.rating,
        comments=feedback.comments,
        categories=feedback.categories,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
