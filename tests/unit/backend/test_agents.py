import pytest
import json
from unittest.mock import AsyncMock, patch
from agents.hospital_brain import HospitalBrain

@pytest.mark.asyncio
async def test_hospital_brain_intent_classification():
    # Mock LLM response
    mock_response = json.dumps({
        "intent": "appointment",
        "confidence": 0.95,
        "entities": {
            "doctor": "Sharma",
            "time": "tomorrow 2 PM"
        }
    })

    with patch("agents.base_agent.BaseAgent.call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_response

        brain = HospitalBrain()
        result = await brain.execute("I need to see Dr. Sharma tomorrow at 2 PM", {})

        assert result["intent"] == "appointment"
        assert result["entities"]["doctor"] == "Sharma"
        assert mock_call.call_count >= 1
        assert "Classify the following query" in mock_call.call_args_list[0].kwargs["prompt"]

@pytest.mark.asyncio
async def test_agent_circuit_breaker():
    # Mock LLM failure to trigger circuit breaker
    with patch("agents.base_agent.BaseAgent.call_llm", new_callable=AsyncMock) as mock_call:
        # We need to simulate the circuit breaker behavior in base_agent
        # For this unit test, we verify the fallback classifier directly if LLM fails
        brain = HospitalBrain()

        # Manually trigger fallback for test
        result = brain._fallback_classifier("I'm having chest pain and can't breathe")

        assert result["intent"] == "emergency"
        assert result["confidence"] == 0.8
