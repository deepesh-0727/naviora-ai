from datetime import datetime

import pytest

from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.emergency import EmergencyCase
from app.models.hospital import Feedback
from app.models.queue import QueueEntry
from app.models.user import User
from app.models.voice_interaction import VoiceInteraction


@pytest.mark.asyncio
async def test_pilot_metrics_are_computed_from_persisted_rows(async_client, db_session):
    admin = User(
        phone="+919811003001",
        email="pilot.admin@test.example",
        password_hash="hash",
        role="admin",
        is_active=True,
        last_login=datetime(2026, 10, 15, 10),
    )
    staff_today = User(
        phone="+919811003002",
        email="pilot.staff.today@test.example",
        password_hash="hash",
        role="staff",
        is_active=True,
        last_login=datetime(2026, 10, 15, 9),
    )
    staff_week = User(
        phone="+919811003003",
        email="pilot.staff.week@test.example",
        password_hash="hash",
        role="doctor",
        is_active=True,
        last_login=datetime(2026, 10, 11, 9),
    )
    db_session.add_all([admin, staff_today, staff_week])
    await db_session.flush()

    db_session.add(
        QueueEntry(
            appointment_id=101,
            doctor_id=1,
            position=1,
            status="served",
            entered_at=datetime(2026, 10, 5, 10),
            served_at=datetime(2026, 10, 5, 10, 12),
        )
    )
    db_session.add(
        EmergencyCase(
            patient_id=None,
            status="resolved",
            priority="CRITICAL",
            location_desc="Pilot ward",
            created_at=datetime(2026, 10, 5, 10),
            arrival_time=datetime(2026, 10, 5, 10, 2, 25),
        )
    )
    db_session.add_all([
        Appointment(
            patient_id=1,
            doctor_id=1,
            department_id=1,
            scheduled_time=datetime(2026, 10, 5, 10),
            status="no_show",
        ),
        Appointment(
            patient_id=2,
            doctor_id=1,
            department_id=1,
            scheduled_time=datetime(2026, 10, 6, 10),
            status="completed",
        ),
    ])
    db_session.add_all([
        VoiceInteraction(
            user_id=staff_today.id,
            role="staff",
            transcript="Book cardiology",
            intent="appointment",
            confidence=0.9,
            entities_json={},
            fallback_used=False,
            response_text="Recorded",
            created_at=datetime(2026, 10, 5, 10),
            reviewed_correct=True,
            reviewed_at=datetime(2026, 10, 6, 10),
        ),
        VoiceInteraction(
            user_id=staff_today.id,
            role="staff",
            transcript="Need directions",
            intent="navigation",
            confidence=0.5,
            entities_json={},
            fallback_used=True,
            response_text="Please clarify",
            created_at=datetime(2026, 10, 5, 11),
            reviewed_correct=False,
            reviewed_at=datetime(2026, 10, 6, 11),
        ),
    ])
    db_session.add(
        Feedback(
            appointment_id=1,
            patient_id=1,
            rating=5,
            nps_score=9,
            created_at=datetime(2026, 10, 7, 10),
        )
    )
    await db_session.commit()
    token = create_access_token(subject=admin.id, claims={"role": "admin"})

    response = await async_client.get(
        "/api/v1/admin/pilot/metrics",
        params={"start": "2026-10-01T00:00:00", "end": "2026-10-16T00:00:00"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    metrics = response.json()
    assert metrics["wait_time"] == {
        "avg_minutes": 12.0,
        "p50": 12.0,
        "p95": 12.0,
        "sample_size": 1,
    }
    assert metrics["emergency_response"] == {
        "avg_seconds": 145.0,
        "sample_size": 1,
        "unresolved_created_in_period": 0,
    }
    assert metrics["no_show_rate"] == {"rate": 0.5, "total": 2, "no_shows": 1}
    assert metrics["voice_intents"] == {
        "total": 2,
        "fallback_count": 1,
        "avg_confidence": 0.7,
        "reviewed_accuracy": 0.5,
        "reviewed_sample_size": 2,
    }
    assert metrics["patient_satisfaction"] == {
        "nps": 100.0,
        "nps_responses": 1,
        "promoters": 1,
        "passives": 0,
        "detractors": 0,
        "favorable_rating_share": 1.0,
        "rating_responses": 1,
    }
    assert metrics["active_staff"] == {"daily": 1, "weekly": 2}
    assert metrics["uptime"] == {"last_30d": None, "source": "manual_uptimerobot_review"}


@pytest.mark.asyncio
async def test_pilot_metrics_requires_admin(async_client):
    response = await async_client.get("/api/v1/admin/pilot/metrics")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_pilot_metrics_returns_null_for_empty_samples(async_client, db_session):
    admin = User(
        phone="+919811003099",
        email="pilot.empty.admin@test.example",
        password_hash="hash",
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(subject=admin.id, claims={"role": "admin"})

    response = await async_client.get(
        "/api/v1/admin/pilot/metrics",
        params={"start": "2026-10-13T00:00:00", "end": "2026-10-14T00:00:00"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    metrics = response.json()
    assert metrics["wait_time"] == {
        "avg_minutes": None,
        "p50": None,
        "p95": None,
        "sample_size": 0,
    }
    assert metrics["no_show_rate"] == {"rate": None, "total": 0, "no_shows": 0}
    assert metrics["voice_intents"]["reviewed_accuracy"] is None
    assert metrics["patient_satisfaction"]["nps"] is None
    assert metrics["patient_satisfaction"]["nps_responses"] == 0
    assert metrics["patient_satisfaction"]["promoters"] == 0
    assert metrics["patient_satisfaction"]["passives"] == 0
    assert metrics["patient_satisfaction"]["detractors"] == 0
    assert metrics["uptime"]["last_30d"] is None
