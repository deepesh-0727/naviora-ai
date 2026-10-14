from unittest.mock import AsyncMock

from redis.exceptions import ConnectionError as RedisConnectionError

from app.api.v1.endpoints import health


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
