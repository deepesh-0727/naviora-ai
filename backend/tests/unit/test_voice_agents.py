from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.agents.hospital_brain import HospitalBrain
from app.agents.specialized.appointment_agent import AppointmentAgent
from app.agents.specialized.doctor_assistance_agent import DoctorAssistanceAgent
from app.agents.specialized.emergency_agent import EmergencyAgent
from app.agents.specialized.facility_management_agent import FacilityManagementAgent
from app.agents.specialized.information_agent import InformationAgent
from app.agents.specialized.navigation_agent import NavigationAgent
from app.agents.specialized.pharmacy_agent import PharmacyAgent
from app.agents.specialized.registration_agent import RegistrationAgent


SAMPLE_REQUESTS = (
    "I need help with an appointment",
    "Please show directions to cardiology",
    "I need to ask about my medication",
    "I need help updating registration details",
    "I need assistance with a hospital request",
)


@pytest.mark.asyncio
async def test_specialist_agents_parse_five_sample_requests(monkeypatch):
    cases = (
        (AppointmentAgent(), '{"doctor_specialty":null,"preferred_time":null,"symptoms":null,"is_urgent":false,"is_checkin":false}', {"session_id": "unit", "user_id": 7}),
        (EmergencyAgent(), '{"emergency_type":"unknown","severity":3,"location_clues":null,"immediate_action_required":null}', {"session_id": "unit", "user_id": 7}),
        (NavigationAgent(), '{"destination":null,"current_location":null,"needs_elevator":false,"is_urgent":false}', {"session_id": "unit", "user_id": 7}),
        (PharmacyAgent(), '{"medication_name":null,"query_type":"unknown","quantity":null}', {"session_id": "unit", "user_id": 7}),
        (RegistrationAgent(), '{"first_name":null,"last_name":null,"dob":null,"gender":null,"blood_group":null,"emergency_contact":null}', {"session_id": "unit", "user_id": 7}),
        (DoctorAssistanceAgent(), '{"request_type":"unknown","patient_identifier":null}', {"session_id": "unit", "user_id": 7}),
        (FacilityManagementAgent(), '{"request_type":"unknown","location":null,"description":null}', {"session_id": "unit", "user_id": 7}),
    )
    for agent, response, context in cases:
        monkeypatch.setattr(agent, "call_llm", AsyncMock(return_value=response))
        for query in SAMPLE_REQUESTS:
            result = await agent.execute(query, context)
            assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_hospital_information_is_unavailable_without_verified_content():
    agent = InformationAgent()
    for query in SAMPLE_REQUESTS:
        with pytest.raises(HTTPException) as raised:
            await agent.execute(query, {"user_id": 7})
        assert raised.value.status_code == 501


@pytest.mark.parametrize(
    ("query", "expected"),
    (
        ("I have chest pain, help me", "emergency"),
        ("Please book an appointment", "appointment"),
        ("Show directions to the clinic", "navigation"),
        ("I need a prescription refill", "pharmacy"),
        ("I need a maintenance request", "facility_management"),
    ),
)
def test_rule_classifier_fallback(query, expected):
    analysis = HospitalBrain._rule_classify(query)
    assert analysis["intent"] == expected
    assert analysis["confidence"] >= 0.6


def test_rule_classifier_asks_for_clarification_when_ambiguous():
    analysis = HospitalBrain._rule_classify("Can you help me")
    assert analysis["intent"] is None
    assert analysis["confidence"] == 0.0
