import hashlib
import secrets

from fastapi import HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.services.notification.sms_service import sms_service

OTP_TTL_SECONDS = {
    "patient": 300,
    "staff": 180,
    "doctor": 180,
    "nurse": 180,
    "front_desk": 180,
    "pharmacy": 180,
    "facilities": 180,
    "emergency": 180,
    "admin": 120,
    "super_admin": 120,
}
RATE_LIMIT_SECONDS = 900
MAX_REQUESTS_PER_WINDOW = 3
MAX_VERIFICATION_ATTEMPTS = 3

_RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return count
"""

_VERIFY_SCRIPT = """
if redis.call('EXISTS', KEYS[3]) == 1 then return -2 end
local expected = redis.call('GET', KEYS[1])
if not expected then return 0 end
if expected == ARGV[1] then
  redis.call('DEL', KEYS[1], KEYS[2])
  return 1
end
local attempts = redis.call('INCR', KEYS[2])
if attempts == 1 then redis.call('EXPIRE', KEYS[2], ARGV[2]) end
if attempts >= tonumber(ARGV[3]) then
  redis.call('SET', KEYS[3], '1', 'EX', ARGV[4])
  redis.call('DEL', KEYS[1], KEYS[2])
  return -1
end
return 0
"""


def _phone_key(phone: str) -> str:
    digest = hashlib.sha256(phone.strip().encode("utf-8")).hexdigest()
    return digest


class OTPService:
    async def generate(self, phone: str, role: str) -> int:
        ttl = OTP_TTL_SECONDS.get(role)
        if ttl is None:
            raise HTTPException(status_code=403, detail="OTP is not available for this account role.")
        phone_hash = _phone_key(phone)
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            lock_key = f"naviora:otp:lock:{phone_hash}"
            if await redis.exists(lock_key):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="OTP verification is locked. Try again in 15 minutes.",
                )
            request_count = await redis.eval(
                _RATE_LIMIT_SCRIPT,
                1,
                f"naviora:otp:rate:{phone_hash}",
                RATE_LIMIT_SECONDS,
            )
            if int(request_count) > MAX_REQUESTS_PER_WINDOW:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many OTP requests. Try again in 15 minutes.",
                )

            code = f"{secrets.randbelow(1_000_000):06d}"
            otp_key = f"naviora:otp:code:{phone_hash}"
            await redis.set(otp_key, code, ex=ttl)
            if not await sms_service.send_otp(phone, code, expires_in_seconds=ttl):
                await redis.delete(otp_key)
                raise HTTPException(status_code=503, detail="Unable to deliver OTP SMS.")
            return ttl
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="OTP service is unavailable.") from exc
        finally:
            await redis.aclose()

    async def verify(self, phone: str, code: str) -> str:
        phone_hash = _phone_key(phone)
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            result = int(
                await redis.eval(
                    _VERIFY_SCRIPT,
                    3,
                    f"naviora:otp:code:{phone_hash}",
                    f"naviora:otp:attempts:{phone_hash}",
                    f"naviora:otp:lock:{phone_hash}",
                    code,
                    RATE_LIMIT_SECONDS,
                    MAX_VERIFICATION_ATTEMPTS,
                    RATE_LIMIT_SECONDS,
                )
            )
            if result == 1:
                return "verified"
            if result in {-1, -2}:
                return "locked"
            return "invalid"
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="OTP service is unavailable.") from exc
        finally:
            await redis.aclose()


otp_service = OTPService()
