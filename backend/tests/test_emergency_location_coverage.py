from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import String

from app.core.security import create_access_token
from app.models.emergency import EmergencyCase
from app.models.patient import Patient
from app.models.tracking import LocationTracking
from app.models.user import User
from app.services.ws_manager import ws_manager


@pytest.fixture
async def emergency_api_context(db_session, monkeypatch):
    from app.services.emergency_service import emergency_service

    monkeypatch.setattr(EmergencyCase.__table__.c.location_coords, "type", String())
    monkeypatch.setattr(LocationTracking.__table__.c.location, "type", String())
    patient_user = User(phone="9800001101", email="emergency.patient@tests.example", password_hash="hash", role="patient")
    other_patient_user = User(phone="9800001102", email="emergency.other@tests.example", password_hash="hash", role="patient")
    staff_user = User(phone="9800001103", email="emergency.staff@tests.example", password_hash="hash", role="staff")
    unauthorized_user = User(phone="9800001104", email="emergency.unauthorized@tests.example", password_hash="hash", role="pharmacy")
    second_staff_user = User(phone="9800001106", email="emergency.staff2@tests.example", password_hash="hash", role="staff")
    db_session.add_all([patient_user, other_patient_user, staff_user, unauthorized_user, second_staff_user])
    await db_session.flush()
    patient = Patient(user_id=patient_user.id, first_name="Emergency", last_name="Patient", date_of_birth=datetime(1990, 1, 1), gender="unknown", emergency_contact="", emergency_contact_name="")
    other_patient = Patient(user_id=other_patient_user.id, first_name="Other", last_name="Patient", date_of_birth=datetime(1991, 1, 1), gender="unknown", emergency_contact="", emergency_contact_name="")
    db_session.add_all([patient, other_patient])
    await db_session.flush()
    case = EmergencyCase(patient_id=patient.id, status="triggered", priority="2", location_desc="Ward A", description="Urgent", assigned_staff=None)
    resolved = EmergencyCase(patient_id=patient.id, status="resolved", priority="4", location_desc="Ward B", description="Resolved", assigned_staff=None)
    unassigned_case = EmergencyCase(patient_id=None, status="triggered", priority="3", location_desc="Lobby", description="Walk-in", assigned_staff=None)
    other_case = EmergencyCase(patient_id=other_patient.id, status="triggered", priority="5", location_desc="Ward C", description="Other", assigned_staff=None)
    db_session.add_all([case, resolved, unassigned_case, other_case])
    await db_session.commit()

    broadcast = AsyncMock(return_value=True)
    monkeypatch.setattr(ws_manager, "broadcast_event", broadcast)
    monkeypatch.setattr(emergency_service.agent, "execute", AsyncMock(return_value={"severity": 1, "summary": "critical"}))

    def headers(user):
        return {"Authorization": f"Bearer {create_access_token(subject=user.id, claims={'role': user.role})}"}

    return {"patient": patient, "patient_user": patient_user, "other_patient": other_patient,
            "staff_user": staff_user, "unauthorized_user": unauthorized_user, "case": case,
            "resolved": resolved, "unassigned_case": unassigned_case, "other_case": other_case,
            "patient_headers": headers(patient_user), "other_headers": headers(other_patient_user),
            "staff_headers": headers(staff_user), "second_staff_headers": headers(second_staff_user),
            "unauthorized_headers": headers(unauthorized_user), "broadcast": broadcast}


@pytest.mark.asyncio
async def test_sos_trigger_persists_case_and_broadcasts_critical_alert(async_client: AsyncClient, emergency_api_context, db_session):
    ctx = emergency_api_context
    response = await async_client.post("/api/v1/emergency/trigger", headers=ctx["patient_headers"], json={"location": "Room 12", "description": "Chest pain"})
    created = await db_session.get(EmergencyCase, response.json()["emergency_id"])
    assert response.status_code == 200 and response.json()["triage"]["severity"] == 1
    assert response.json()["id"] == created.id
    assert created.patient_id == ctx["patient"].id and created.location_desc == "Room 12"
    assert ctx["broadcast"].await_count == 3


@pytest.mark.asyncio
async def test_sos_requires_patient_profile_and_supports_staff(async_client: AsyncClient, emergency_api_context, db_session):
    ctx = emergency_api_context
    no_profile = User(phone="9800001105", email="emergency.no.profile@tests.example", password_hash="hash", role="patient")
    db_session.add(no_profile)
    await db_session.commit()
    no_profile_headers = {"Authorization": f"Bearer {create_access_token(subject=no_profile.id, claims={'role': 'patient'})}"}
    missing = await async_client.post("/api/v1/emergency/sos", headers=no_profile_headers, json={"location": "Gate", "description": "Need help"})
    staff = await async_client.post("/api/v1/emergency/sos", headers=ctx["staff_headers"], json={"location": "Lobby"})
    assert (missing.status_code, missing.json()["detail"]) == (404, "Patient profile not found.")
    assert staff.status_code == 200 and staff.json()["status"] == "SOS triggered successfully"


@pytest.mark.asyncio
async def test_sos_is_persisted_when_triage_service_is_unavailable(async_client: AsyncClient, emergency_api_context, db_session, monkeypatch):
    from app.services.emergency_service import emergency_service

    ctx = emergency_api_context
    monkeypatch.setattr(emergency_service.agent, "execute", AsyncMock(side_effect=RuntimeError("triage offline")))
    response = await async_client.post(
        "/api/v1/emergency/trigger",
        headers=ctx["patient_headers"],
        json={"location": "Room 12", "description": "Chest pain"},
    )

    created = await db_session.get(EmergencyCase, response.json()["id"])
    assert response.status_code == 200
    assert created is not None and created.priority == "2"
    assert response.json()["triage_available"] is False
    assert response.json()["message"] == "Emergency logged. Please call the hospital emergency line immediately."


@pytest.mark.asyncio
async def test_sos_response_remains_successful_when_staff_notification_fails(async_client: AsyncClient, emergency_api_context, db_session):
    ctx = emergency_api_context
    ctx["broadcast"].return_value = False
    response = await async_client.post(
        "/api/v1/emergency/trigger",
        headers=ctx["patient_headers"],
        json={"location": "Room 12", "description": "Chest pain"},
    )

    created = await db_session.get(EmergencyCase, response.json()["id"])
    assert response.status_code == 200
    assert created is not None
    assert response.json()["notification_available"] is False
    assert response.json()["message"] == "Emergency logged. Please call the hospital emergency line immediately."


@pytest.mark.asyncio
async def test_emergency_status_active_and_ownership(async_client: AsyncClient, emergency_api_context):
    ctx = emergency_api_context
    own = await async_client.get(f"/api/v1/emergency/status/{ctx['case'].id}", headers=ctx["patient_headers"])
    foreign = await async_client.get(f"/api/v1/emergency/status/{ctx['other_case'].id}", headers=ctx["patient_headers"])
    missing = await async_client.get("/api/v1/emergency/status/99999", headers=ctx["patient_headers"])
    active = await async_client.get("/api/v1/emergency/active", headers=ctx["staff_headers"])
    assert own.json()["location"] == "Ward A" and own.json()["priority"] == "2"
    assert (foreign.status_code, foreign.json()["detail"]) == (403, "You can only view your own emergency.")
    assert (missing.status_code, missing.json()["detail"]) == (404, "Emergency case not found")
    assert {item["id"] for item in active.json()["items"]} == {ctx["case"].id, ctx["unassigned_case"].id, ctx["other_case"].id}


@pytest.mark.asyncio
async def test_staff_assign_arrive_and_resolve(async_client: AsyncClient, emergency_api_context, db_session):
    ctx = emergency_api_context
    assigned = await async_client.post(f"/api/v1/emergency/respond/{ctx['case'].id}", headers=ctx["staff_headers"])
    conflict = await async_client.post(f"/api/v1/emergency/respond/{ctx['case'].id}", headers=ctx["second_staff_headers"])
    arrived = await async_client.put(f"/api/v1/emergency/staff-arrived?emergency_id={ctx['case'].id}", headers=ctx["staff_headers"])
    resolved = await async_client.put(f"/api/v1/emergency/resolve/{ctx['case'].id}", headers=ctx["staff_headers"])
    await db_session.refresh(ctx["case"])
    assert assigned.json() == {"emergency_id": ctx["case"].id, "status": "staff_assigned", "staff_id": ctx["staff_user"].id}
    assert (conflict.status_code, conflict.json()["detail"]) == (409, "This emergency is already assigned to another staff member.")
    assert arrived.json()["status"] == "staff_arrived" and arrived.json()["arrival_time"]
    assert resolved.json() == {"id": ctx["case"].id, "status": "resolved"} and ctx["case"].status == "resolved"


@pytest.mark.asyncio
async def test_emergency_rejects_unauthorized_resolved_and_unassigned_actions(async_client: AsyncClient, emergency_api_context):
    ctx = emergency_api_context
    denied = await async_client.get(f"/api/v1/emergency/status/{ctx['case'].id}", headers=ctx["unauthorized_headers"])
    resolved_assign = await async_client.post(f"/api/v1/emergency/respond/{ctx['resolved'].id}", headers=ctx["staff_headers"])
    missing = await async_client.post("/api/v1/emergency/staff-acknowledge?emergency_id=99999", headers=ctx["staff_headers"])
    arrived_unassigned = await async_client.put(f"/api/v1/emergency/staff-arrived?emergency_id={ctx['case'].id}", headers=ctx["staff_headers"])
    assert (denied.status_code, denied.json()["detail"]) == (403, "You are not authorized to view emergencies.")
    assert (resolved_assign.status_code, resolved_assign.json()["detail"]) == (409, "Resolved emergencies cannot be assigned.")
    assert (missing.status_code, missing.json()["detail"]) == (404, "Emergency case not found.")
    assert (arrived_unassigned.status_code, arrived_unassigned.json()["detail"]) == (403, "Only the assigned responder can mark arrival.")


@pytest.mark.asyncio
async def test_resolve_rejects_foreign_patient_and_broadcasts_for_unlinked_case(async_client: AsyncClient, emergency_api_context):
    ctx = emergency_api_context
    foreign = await async_client.put(f"/api/v1/emergency/resolve/{ctx['other_case'].id}", headers=ctx["patient_headers"])
    unlinked = await async_client.put(f"/api/v1/emergency/resolve/{ctx['unassigned_case'].id}", headers=ctx["staff_headers"])
    assert (foreign.status_code, foreign.json()["detail"]) == (403, "You can only resolve your own emergency.")
    assert unlinked.json() == {"id": ctx["unassigned_case"].id, "status": "resolved"}


@pytest.mark.asyncio
async def test_location_update_nearby_staff_and_emergency_nearby(async_client: AsyncClient, emergency_api_context, db_session):
    ctx = emergency_api_context
    updated = await async_client.post("/api/v1/location/update", headers=ctx["staff_headers"], json={"user_id": ctx["staff_user"].id, "latitude": 12.9716, "longitude": 77.5946, "floor": 1, "building": "A"})
    updated_again = await async_client.post("/api/v1/location/update", headers=ctx["staff_headers"], json={"user_id": ctx["staff_user"].id, "latitude": 12.9717, "longitude": 77.5947, "floor": 2, "building": "B"})
    nearby = await async_client.get("/api/v1/emergency/nearby-staff?latitude=12.9716&longitude=77.5946", headers=ctx["staff_headers"])
    assert updated.status_code == 200 and updated.json()["building"] == "A"
    assert updated_again.status_code == 200 and updated_again.json()["floor"] == 2
    assert nearby.json()["staff"][0]["staff_id"] == ctx["staff_user"].id
