"""OTP tests use fakeredis so Redis Lua and key TTL behavior remain local."""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock

from app.services import otp_service as otp_module
from app.services.otp_service import OTPService, _phone_key


@pytest.fixture
def fake_redis(monkeypatch):
    # Local environments without the dev extra cannot exercise Redis scripts;
    # CI installs fakeredis[lua] from backend/requirements-dev.txt.
    fakeredis = pytest.importorskip("fakeredis.aioredis", reason="fakeredis[lua] dev dependency is unavailable")
    redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(otp_module.Redis, "from_url", lambda *args, **kwargs: redis)
    return redis


@pytest.mark.asyncio
async def test_otp_generate_patient_sets_expected_ttl(fake_redis, monkeypatch):
    sms = AsyncMock(return_value=True)
    monkeypatch.setattr(otp_module.sms_service, "send_otp", sms)

    ttl = await OTPService().generate("+919800000001", "patient")

    key = f"naviora:otp:code:{_phone_key('+919800000001')}"
    assert ttl == 300
    assert await fake_redis.ttl(key) == 300
    assert sms.await_args.args[0] == "+919800000001"
    assert len(sms.await_args.args[1]) == 6


@pytest.mark.asyncio
async def test_otp_verify_correct_code_returns_verified(fake_redis, monkeypatch):
    monkeypatch.setattr(otp_module.sms_service, "send_otp", AsyncMock(return_value=True))
    await OTPService().generate("+919800000002", "patient")
    key = f"naviora:otp:code:{_phone_key('+919800000002')}"
    code = await fake_redis.get(key)

    assert await OTPService().verify("+919800000002", code) == "verified"


@pytest.mark.asyncio
async def test_otp_verify_wrong_code_returns_invalid(fake_redis):
    await fake_redis.set(f"naviora:otp:code:{_phone_key('+919800000003')}", "123456", ex=300)

    assert await OTPService().verify("+919800000003", "000000") == "invalid"


@pytest.mark.asyncio
async def test_otp_verify_expired_code_returns_invalid(fake_redis):
    key = f"naviora:otp:code:{_phone_key('+919800000004')}"
    await fake_redis.set(key, "123456", ex=300)
    await fake_redis.delete(key)

    assert await OTPService().verify("+919800000004", "123456") == "invalid"


@pytest.mark.asyncio
async def test_otp_generate_exceeding_three_requests_is_rate_limited(fake_redis, monkeypatch):
    sms = AsyncMock(return_value=True)
    monkeypatch.setattr(otp_module.sms_service, "send_otp", sms)
    service = OTPService()
    phone = "+919800000005"

    for _ in range(3):
        await service.generate(phone, "patient")
    with pytest.raises(HTTPException) as error:
        await service.generate(phone, "patient")

    assert error.value.status_code == 429
    assert sms.await_count == 3


@pytest.mark.asyncio
async def test_otp_verify_third_wrong_attempt_locks_account(fake_redis):
    phone = "+919800000006"
    await fake_redis.set(f"naviora:otp:code:{_phone_key(phone)}", "123456", ex=300)
    service = OTPService()

    assert await service.verify(phone, "000001") == "invalid"
    assert await service.verify(phone, "000002") == "invalid"
    assert await service.verify(phone, "000003") == "locked"
    assert await service.verify(phone, "123456") == "locked"
