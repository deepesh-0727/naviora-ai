import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.models.appointment import Appointment
from app.models.doctor import Doctor, Department

@pytest.mark.asyncio
async def test_calculate_wait_time(client: AsyncClient, db_session: AsyncSession):
    # Setup: Create a doctor
    dept = Department(name="Test Dept", floor=1, wing="A", building="Main", phone="123", email="test@test.com")
    db_session.add(dept)
    await db_session.flush()

    doctor = Doctor(
        user_id=1, # Mock user_id
        first_name="Test",
        last_name="Doctor",
        specialization="General",
        department_id=dept.id,
        license_number="LIC-123",
        years_of_experience=10,
        avg_consultation_time=20
    )
    db_session.add(doctor)
    await db_session.commit()

    # Test wait time API
    response = await client.get(f"/api/v1/queue/wait-time/{doctor.id}?position=3")
    assert response.status_code == 200
    assert response.json()["estimated_wait_minutes"] == 60 # 3 * 20
