from datetime import datetime

import pytest

from app.models.appointment import Appointment


@pytest.mark.asyncio
async def test_staff_journey_views_queue_marks_in_room_and_completes_consultation(async_client, hospital_actors, db_session):
    patient = hospital_actors["patient_profile"]
    doctor = hospital_actors["doctor_profile"]
    department = hospital_actors["department"]
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        department_id=department.id,
        status="check_in",
        queue_position=1,
        scheduled_time=datetime(2035, 6, 15, 9),
    )
    db_session.add(appointment)
    await db_session.commit()
    await db_session.refresh(appointment)
    headers = {"Authorization": f"Bearer {hospital_actors['tokens']['doctor']}"}

    queue = await async_client.get("/api/v1/staff/doctor/queue", headers=headers)
    assert queue.status_code == 200
    assert len(queue.json()["items"]) == 1
    assert queue.json()["items"][0]["id"] == appointment.id
    assert queue.json()["items"][0]["status"] == "check_in"

    in_room = await async_client.put(
        f"/api/v1/staff/queue/{appointment.id}/status",
        headers=headers,
        json={"status": "in_room"},
    )
    assert in_room.status_code == 200
    assert in_room.json()["status"] == "treating"
    assert in_room.json()["id"] == appointment.id

    completed = await async_client.put(
        f"/api/v1/staff/queue/{appointment.id}/status",
        headers=headers,
        json={"status": "completed"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["queue_position"] == 0
