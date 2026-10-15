from unittest.mock import AsyncMock

import pytest

from app.services import emergency_service as emergency_module


@pytest.mark.asyncio
async def test_emergency_journey_sos_assign_en_route_and_arrival(async_client, hospital_actors, monkeypatch):
    monkeypatch.setattr(
        emergency_module.emergency_service.agent,
        "execute",
        AsyncMock(return_value={
            "emergency_type": "chest pain",
            "severity": 2,
            "location_clues": "main lobby",
            "immediate_action_required": "wait for the response team",
        }),
    )
    patient_headers = {"Authorization": f"Bearer {hospital_actors['tokens']['patient']}"}
    created = await async_client.post(
        "/api/v1/emergency/sos",
        headers=patient_headers,
        json={"location": "Main lobby", "description": "chest pain"},
    )
    assert created.status_code == 200
    case = created.json()
    assert case["status"] == "SOS triggered successfully"
    assert case["emergency_id"] > 0
    assert case["triage"]["severity"] == 2

    responder_headers = {"Authorization": f"Bearer {hospital_actors['tokens']['responder']}"}
    assigned = await async_client.post(
        f"/api/v1/staff/emergency/{case['emergency_id']}/assign",
        headers=responder_headers,
        json={"responder_id": hospital_actors["responder"].id},
    )
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "staff_assigned"
    assert assigned.json()["responder_id"] == hospital_actors["responder"].id

    en_route = await async_client.put(
        f"/api/v1/staff/emergency/{case['emergency_id']}/status",
        headers=responder_headers,
        json={"status": "en_route"},
    )
    assert en_route.status_code == 200
    assert en_route.json()["status"] == "en_route"
    assert en_route.json()["emergency_id"] == case["emergency_id"]

    arrived = await async_client.put(
        f"/api/v1/staff/emergency/{case['emergency_id']}/status",
        headers=responder_headers,
        json={"status": "arrived"},
    )
    assert arrived.status_code == 200
    assert arrived.json()["status"] == "arrived"
    assert arrived.json()["emergency_id"] == case["emergency_id"]
