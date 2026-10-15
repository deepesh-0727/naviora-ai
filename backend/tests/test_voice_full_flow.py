"""Authenticated API coverage for voice booking, using test DB and configured Redis."""

from sqlalchemy import func, select

import pytest

from app.agents.base_agent import BaseAgent
from app.core.config import settings
from app.models.appointment import Appointment
from app.services.voice_pending_service import voice_pending_service


def _voice_headers(actors):
    return {"Authorization": f"Bearer {actors['tokens']['patient']}"}


async def _turn(async_client, actors, text):
    return await async_client.post(
        "/api/v1/voice/process-text",
        headers=_voice_headers(actors),
        json={"text": text, "session_id": "full-flow-session"},
    )


def _use_deterministic_ollama(monkeypatch):
    async def ollama_response(self, prompt, system=None, model=None):
        if self.name == "HospitalBrain":
            return (
                '{"intent":"appointment","confidence":0.95,'
                '"entities":{"doctor":"Doctor Journey",'
                '"date":"2035-06-15","time":"09:00:00"}}'
            )
        if self.name == "AppointmentAgent":
            return (
                '{"doctor_specialty":null,"preferred_time":"2035-06-15T09:00:00",'
                '"symptoms":"test","is_urgent":false,"is_checkin":false}'
            )
        raise AssertionError(f"Unexpected LLM agent in voice booking: {self.name}")

    monkeypatch.setattr(BaseAgent, "_call_ollama", ollama_response)


@pytest.mark.asyncio
async def test_voice_full_happy_path_llm_available(
    async_client, hospital_actors, configured_test_redis_url, monkeypatch
):
    monkeypatch.setattr(settings, "REDIS_URL", configured_test_redis_url)
    monkeypatch.setattr(settings, "CACHE_ENABLED", False)
    _use_deterministic_ollama(monkeypatch)
    user_id = hospital_actors["patient"].id
    await voice_pending_service.clear_pending(user_id)

    response = await _turn(
        async_client,
        hospital_actors,
        "Book appointment with Doctor Journey at 9 AM on June 15 happy-llm",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["intent"] == "appointment"
    assert body["fallback_used"] is False
    assert body["fallback_reason"] is None
    assert body["analysis"]["appointment_result"]["needs_confirmation"] is True
    assert await voice_pending_service.get_pending(user_id) is not None
    await voice_pending_service.clear_pending(user_id)


@pytest.mark.asyncio
async def test_voice_full_happy_path_llm_unreachable_uses_fallback(
    async_client, hospital_actors, configured_test_redis_url, monkeypatch
):
    import httpx

    monkeypatch.setattr(settings, "REDIS_URL", configured_test_redis_url)
    monkeypatch.setattr(settings, "CACHE_ENABLED", False)
    monkeypatch.setattr(settings, "AI_MAX_RETRIES", 1)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")

    async def ollama_unavailable(self, *_args, **_kwargs):
        raise httpx.ConnectError("test Ollama connection refused")

    monkeypatch.setattr(BaseAgent, "_call_ollama", ollama_unavailable)
    user_id = hospital_actors["patient"].id
    await voice_pending_service.clear_pending(user_id)

    response = await _turn(
        async_client,
        hospital_actors,
        "Book appointment with Dr. Journey on 2035-06-15 at 9 AM llm-fallback",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["fallback_used"] is True
    assert body["fallback_reason"] == "llm_unreachable"
    assert body["intent"] == "appointment"
    assert body["analysis"]["appointment_result"]["needs_confirmation"] is True
    assert await voice_pending_service.get_pending(user_id) is not None
    await voice_pending_service.clear_pending(user_id)


@pytest.mark.asyncio
async def test_voice_unauthorized_returns_401(async_client):
    response = await async_client.post("/api/v1/voice/process-text", json={"text": "Book an appointment"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_voice_booking_needs_confirmation_creates_no_row(
    async_client, hospital_actors, db_session, configured_test_redis_url, monkeypatch
):
    monkeypatch.setattr(settings, "REDIS_URL", configured_test_redis_url)
    monkeypatch.setattr(settings, "CACHE_ENABLED", False)
    _use_deterministic_ollama(monkeypatch)
    user_id = hospital_actors["patient"].id
    await voice_pending_service.clear_pending(user_id)

    response = await _turn(
        async_client,
        hospital_actors,
        "Book appointment with Doctor Journey at 9 AM on June 15 proposal-only",
    )

    assert response.status_code == 200, response.text
    assert response.json()["analysis"]["appointment_result"]["needs_confirmation"] is True
    assert await db_session.scalar(select(func.count(Appointment.id))) == 0
    assert await voice_pending_service.get_pending(user_id) is not None
    await voice_pending_service.clear_pending(user_id)


@pytest.mark.asyncio
async def test_voice_booking_confirm_creates_row_and_clears_pending(
    async_client, hospital_actors, db_session, configured_test_redis_url, monkeypatch
):
    monkeypatch.setattr(settings, "REDIS_URL", configured_test_redis_url)
    monkeypatch.setattr(settings, "CACHE_ENABLED", False)
    _use_deterministic_ollama(monkeypatch)
    user_id = hospital_actors["patient"].id
    await voice_pending_service.clear_pending(user_id)
    proposal = await _turn(
        async_client,
        hospital_actors,
        "Book appointment with Doctor Journey at 9 AM on June 15 confirm-flow",
    )
    assert proposal.status_code == 200, proposal.text

    confirmed = await _turn(async_client, hospital_actors, "yes")

    assert confirmed.status_code == 200, confirmed.text
    assert "Appointment confirmed" in confirmed.json()["response_text"]
    assert await db_session.scalar(select(func.count(Appointment.id))) == 1
    assert await voice_pending_service.get_pending(user_id) is None


@pytest.mark.asyncio
async def test_voice_booking_cancel_clears_pending_without_creating_row(
    async_client, hospital_actors, db_session, configured_test_redis_url, monkeypatch
):
    monkeypatch.setattr(settings, "REDIS_URL", configured_test_redis_url)
    monkeypatch.setattr(settings, "CACHE_ENABLED", False)
    _use_deterministic_ollama(monkeypatch)
    user_id = hospital_actors["patient"].id
    await voice_pending_service.clear_pending(user_id)
    proposal = await _turn(
        async_client,
        hospital_actors,
        "Book appointment with Doctor Journey at 9 AM on June 15 cancel-flow",
    )
    assert proposal.status_code == 200, proposal.text

    cancelled = await _turn(async_client, hospital_actors, "no")

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["analysis"]["appointment_result"]["cancelled"] is True
    assert await db_session.scalar(select(func.count(Appointment.id))) == 0
    assert await voice_pending_service.get_pending(user_id) is None
