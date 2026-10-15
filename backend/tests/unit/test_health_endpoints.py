from unittest.mock import AsyncMock

from redis.exceptions import ConnectionError as RedisConnectionError
from httpx import ASGITransport, AsyncClient
import pytest

from app.api.v1.endpoints import health
from app.core import sentry as sentry_service
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.models.user import User
from app.core.rate_limiter import limiter
from app.utils import health_check


class HealthyRedis:
    async def ping(self):
        return True

    async def info(self, section):
        return {"redis_version": "7.2.0"} if section == "server" else {"connected_clients": 3}

    async def aclose(self):
        return None


class UnhealthyRedis:
    async def ping(self):
        raise RedisConnectionError("not reachable")

    async def aclose(self):
        return None


def test_liveness_does_not_probe_dependencies(client, monkeypatch):
    monkeypatch.setattr(health, "_check_database", AsyncMock(side_effect=AssertionError("must not probe")))
    monkeypatch.setattr(health, "_check_redis", AsyncMock(side_effect=AssertionError("must not probe")))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_unreachable_redis(client, monkeypatch):
    monkeypatch.setattr(health.Redis, "from_url", lambda *_args, **_kwargs: UnhealthyRedis())

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "dependencies": {"database": "reachable", "redis": "unreachable"},
    }


def test_readiness_reports_unreachable_database(client, monkeypatch):
    monkeypatch.setattr(health, "_check_database", AsyncMock(return_value=(False, None)))
    monkeypatch.setattr(health.Redis, "from_url", lambda *_args, **_kwargs: HealthyRedis())

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["dependencies"] == {
        "database": "unreachable",
        "redis": "reachable",
    }


def test_readiness_returns_200_when_real_db_and_redis_respond(client, monkeypatch):
    monkeypatch.setattr(health.Redis, "from_url", lambda *_args, **_kwargs: HealthyRedis())

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {"database": "reachable", "redis": "reachable"},
    }


def test_health_details_requires_admin_auth(client):
    response = client.get("/health/details")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_debug_sentry_is_admin_only_and_reports_disabled_state(async_client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", "")
    user = User(phone="+919811000001", email="sentry.admin@test.example", password_hash="hash", role="admin")
    db_session.add(user)
    await db_session.flush()
    token = create_access_token(subject=user.id, claims={"role": "admin"})

    unauthenticated = await async_client.get("/debug/sentry")
    assert unauthenticated.status_code == 401

    response = await async_client.get("/debug/sentry", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503
    assert "configure SENTRY_DSN" in response.json()["detail"]


@pytest.mark.asyncio
async def test_debug_sentry_captures_event_when_configured(db_session, monkeypatch):
    import sentry_sdk
    from sentry_sdk.transport import Transport

    captured_envelopes = []

    class RecordingTransport(Transport):
        def capture_envelope(self, envelope):
            captured_envelopes.append(envelope)

    monkeypatch.setattr(settings, "SENTRY_DSN", "https://public@example.invalid/1")
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    assert sentry_service.init_sentry(transport=RecordingTransport)

    user = User(phone="+919811000002", email="sentry.event@test.example", password_hash="hash", role="admin")
    db_session.add(user)
    await db_session.flush()
    token = create_access_token(subject=user.id, claims={"role": "admin"})

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://localhost",
        ) as test_client:
            response = await test_client.get("/debug/sentry", headers={"Authorization": f"Bearer {token}"})
        sentry_sdk.flush(timeout=2)
        assert response.status_code == 500
        assert any(
            item.type == "event"
            and "Naviora Sentry verification test event" in str(item.payload.json)
            for envelope in captured_envelopes
            for item in envelope
        )
    finally:
        sentry_sdk.flush(timeout=2)
        sentry_sdk.init(dsn=None)


@pytest.mark.asyncio
async def test_detailed_health_reports_dependency_status_and_uptime(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr(health, "_check_database", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr(health, "_check_redis", AsyncMock(return_value=(True, {"redis_version": "7.2.0"})))
    monkeypatch.setattr(health, "check_ai_service_health", AsyncMock(return_value=True))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as test_client:
        response = await test_client.get("/health/detailed")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"
    assert body["uptime_seconds"] >= 0
    assert body["dependencies"] == {"database": "reachable", "redis": "reachable", "ai": "reachable"}


@pytest.mark.asyncio
async def test_detailed_health_reports_degraded_dependencies(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr(health, "_check_database", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr(health, "_check_redis", AsyncMock(return_value=(False, None)))
    monkeypatch.setattr(health, "check_ai_service_health", AsyncMock(return_value=False))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as test_client:
        response = await test_client.get("/health/detailed")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["dependencies"] == {
        "database": "reachable",
        "redis": "unreachable",
        "ai": "unreachable",
    }


@pytest.mark.asyncio
async def test_ai_health_does_not_treat_configured_openai_key_as_reachability(monkeypatch):
    class UnavailableClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, *_args, **_kwargs):
            return type("Response", (), {"status_code": 503})()

    monkeypatch.setattr(settings, "AI_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "configured-test-key")
    monkeypatch.setattr(health_check.httpx, "AsyncClient", lambda **_kwargs: UnavailableClient())

    assert await health_check.check_ai_service_health() is False


@pytest.mark.asyncio
async def test_detailed_health_rate_limits_public_requests(monkeypatch):
    from limits.storage import MemoryStorage
    from limits.strategies import FixedWindowRateLimiter

    monkeypatch.setattr(health, "_check_database", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr(health, "_check_redis", AsyncMock(return_value=(True, {})))
    monkeypatch.setattr(health, "check_ai_service_health", AsyncMock(return_value=True))
    memory_storage = MemoryStorage()
    monkeypatch.setattr(limiter, "_storage", memory_storage)
    monkeypatch.setattr(limiter, "_limiter", FixedWindowRateLimiter(memory_storage))

    transport = ASGITransport(app=app, client=("192.0.2.201", 1234))
    async with AsyncClient(transport=transport, base_url="http://localhost") as test_client:
        responses = [await test_client.get("/health/detailed") for _ in range(11)]

    assert all(response.status_code == 200 for response in responses[:10]), [
        (response.status_code, response.text) for response in responses
    ]
    assert responses[10].status_code == 429
