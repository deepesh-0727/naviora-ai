from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def user_or_ip_key(request: Request) -> str:
    claims = getattr(request.state, "auth_claims", {})
    subject = claims.get("sub") if isinstance(claims, dict) else None
    if subject:
        return f"user:{subject}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    in_memory_fallback_enabled=False,
    headers_enabled=True,
)
