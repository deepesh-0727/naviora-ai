from datetime import datetime

import pytest

from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.hospital import Feedback
from app.models.patient import Patient
from app.models.user import User


async def _feedback_request_context(db_session):
    user = User(
        phone="+919811002001",
        email="feedback.patient@test.example",
        password_hash="hash",
        role="patient",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    patient = Patient(
        user_id=user.id,
        first_name="Test",
        last_name="Patient",
        date_of_birth=datetime(1990, 1, 1),
        gender="unknown",
        emergency_contact="",
        emergency_contact_name="",
    )
    db_session.add(patient)
    await db_session.flush()
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=1,
        department_id=1,
        scheduled_time=datetime(2026, 10, 14, 10),
        status="completed",
    )
    db_session.add(appointment)
    await db_session.flush()
    await db_session.commit()
    token = create_access_token(subject=user.id, claims={"role": "patient"})
    return appointment, {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_feedback_persists_nps_score(async_client, db_session):
    appointment, headers = await _feedback_request_context(db_session)

    response = await async_client.post(
        "/api/v1/feedback",
        headers=headers,
        json={"appointment_id": appointment.id, "rating": 5, "nps_score": 9},
    )

    assert response.status_code == 201
    assert response.json()["nps_score"] == 9
    feedback = await db_session.get(Feedback, response.json()["id"])
    assert feedback.nps_score == 9


@pytest.mark.asyncio
@pytest.mark.parametrize("nps_score", [11, 15])
async def test_feedback_rejects_nps_scores_above_ten(async_client, db_session, nps_score):
    appointment, headers = await _feedback_request_context(db_session)

    response = await async_client.post(
        "/api/v1/feedback",
        headers=headers,
        json={"appointment_id": appointment.id, "rating": 5, "nps_score": nps_score},
    )

    assert response.status_code == 422
