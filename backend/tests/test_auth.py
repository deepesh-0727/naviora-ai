"""
Unit tests for /api/v1/auth/* endpoints.

All external dependencies (Redis, SMS) are mocked so these tests
run in CI without any live services.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Health check (smoke test — always runs first)
# ---------------------------------------------------------------------------

def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "ok"


# ---------------------------------------------------------------------------
# OTP generation
# ---------------------------------------------------------------------------

def _mock_redis_ctx(stored_otp=None):
    """Return a patched Redis that records set/get/delete calls."""
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    mock_redis.get.return_value = stored_otp
    mock_redis.delete.return_value = True
    mock_redis.aclose.return_value = None

    mock_cls = MagicMock()
    mock_cls.return_value = mock_redis
    return mock_cls, mock_redis


@pytest.mark.asyncio
async def test_otp_generate_success(client):
    """OTP generation should return 200 and confirmation message."""
    mock_cls, _ = _mock_redis_ctx()
    with patch("redis.asyncio.Redis.from_url", mock_cls):
        with patch(
            "app.services.notification.sms_service.sms_service.send_otp",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = client.post("/api/v1/auth/otp/generate?phone=%2B919876543210")
            assert resp.status_code == 200
            body = resp.json()
            assert body["message"] == "OTP sent successfully"
            assert body["expires_in_seconds"] == 300


@pytest.mark.asyncio
async def test_otp_generate_sms_failure_returns_503(client):
    """If SMS delivery fails, the OTP should be deleted and 503 returned."""
    mock_cls, mock_redis = _mock_redis_ctx()
    with patch("redis.asyncio.Redis.from_url", mock_cls):
        with patch(
            "app.services.notification.sms_service.sms_service.send_otp",
            new_callable=AsyncMock,
            return_value=False,  # <-- simulate delivery failure
        ):
            resp = client.post("/api/v1/auth/otp/generate?phone=%2B919876543210")
            assert resp.status_code == 503
            # OTP key must have been cleaned up
            mock_redis.delete.assert_called_once()


# ---------------------------------------------------------------------------
# OTP verification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_otp_verify_correct_code(client):
    """Correct OTP code should verify successfully."""
    mock_cls, _ = _mock_redis_ctx(stored_otp="482910")
    with patch("redis.asyncio.Redis.from_url", mock_cls):
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "+919876543210", "code": "482910"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "OTP verified successfully"


@pytest.mark.asyncio
async def test_otp_verify_wrong_code_returns_400(client):
    """Wrong OTP code should return 400 Bad Request."""
    mock_cls, _ = _mock_redis_ctx(stored_otp="482910")
    with patch("redis.asyncio.Redis.from_url", mock_cls):
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "+919876543210", "code": "000000"},
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_otp_verify_expired_returns_400(client):
    """Expired (missing) OTP should return 400 Bad Request."""
    mock_cls, _ = _mock_redis_ctx(stored_otp=None)  # key expired / not found
    with patch("redis.asyncio.Redis.from_url", mock_cls):
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "+919876543210", "code": "123456"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_missing_credentials_returns_422(client):
    """Empty form body should return 422 Unprocessable Entity."""
    resp = client.post("/api/v1/auth/login", data={})
    assert resp.status_code == 422


def test_login_wrong_password_returns_400(client):
    """Login with a non-existent user should return 400."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "+919999999999", "password": "wrongpassword"},
    )
    # auth_service returns None → 400 Bad Request
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

def test_refresh_token_invalid_returns_400(client):
    """A garbage refresh token should return 400 Bad Request."""
    resp = client.post(
        "/api/v1/auth/refresh",
        params={"refresh_token": "not.a.valid.jwt"},
    )
    assert resp.status_code == 400


def test_refresh_token_empty_returns_400(client):
    """An empty string refresh token should return 400."""
    resp = client.post(
        "/api/v1/auth/refresh",
        params={"refresh_token": ""},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Logout & password reset stubs
# ---------------------------------------------------------------------------

def test_logout_returns_200(client):
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert "Logged out" in resp.json()["message"]


def test_forgot_password_returns_200(client):
    resp = client.post(
        "/api/v1/auth/forgot-password",
        params={"email": "test@naviora.ai"},
    )
    assert resp.status_code == 200
