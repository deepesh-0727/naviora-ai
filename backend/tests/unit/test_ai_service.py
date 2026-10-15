from unittest.mock import AsyncMock

import httpx
import pytest

from app.agents.hospital_brain import HospitalBrain


@pytest.mark.asyncio
async def test_ai_ollama_request_parses_response_from_mock_http_transport(monkeypatch):
    class MockAsyncClient:
        def __init__(self, **kwargs):
            self.timeout = kwargs["timeout"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            assert url.endswith("/api/generate")
            assert json["stream"] is False
            return httpx.Response(200, json={"response": " {\"intent\": \"appointment\"} "})

    monkeypatch.setattr("app.agents.base_agent.httpx.AsyncClient", MockAsyncClient)
    brain = HospitalBrain(ollama_url="http://ollama.test")

    response = await brain._call_ollama("book a visit")

    assert response == '{"intent": "appointment"}'


@pytest.mark.asyncio
async def test_ai_classifier_uses_rule_fallback_when_model_is_unavailable(monkeypatch):
    from app.services import cache_service as cache_module

    monkeypatch.setattr(cache_module.cache_service, "get_cached_intent", AsyncMock(return_value=None))
    save_result = AsyncMock(return_value=True)
    monkeypatch.setattr(cache_module.cache_service, "set_cached_intent", save_result)
    brain = HospitalBrain()
    monkeypatch.setattr(brain, "call_llm", AsyncMock(side_effect=RuntimeError("offline")))

    result = await brain.execute("an unclear request", {"user_id": "test-user"})

    assert result["intent"] is None
    assert result["confidence"] == 0.0
    assert result["needs_clarification"] is True
    save_result.assert_awaited_once()


@pytest.mark.asyncio
async def test_ai_classifier_returns_cached_intent_without_model_request(monkeypatch):
    from app.services import cache_service as cache_module

    cached = {"intent": "appointment", "confidence": 0.8, "entities": {}}
    monkeypatch.setattr(cache_module.cache_service, "get_cached_intent", AsyncMock(return_value=cached))
    monkeypatch.setattr(cache_module.cache_service, "set_cached_intent", AsyncMock())
    brain = HospitalBrain()
    model_call = AsyncMock()
    monkeypatch.setattr(brain, "call_llm", model_call)
    details = {"doctor": "Dr Sen"}
    monkeypatch.setattr(brain.appointment_agent, "execute", AsyncMock(return_value=details))

    result = await brain.execute("book an appointment", {"user_id": "test-user"})

    assert result["intent"] == "appointment"
    assert result["specialized_details"] == details
    model_call.assert_not_awaited()
