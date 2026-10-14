import logging
from time import perf_counter

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.models.hospital import AuditLog

logger = logging.getLogger(__name__)
SENSITIVE_PREFIXES = ("/api/v1/patients", "/api/v1/staff", "/api/v1/admin")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        started = perf_counter()
        response = await call_next(request)
        path = request.url.path.rstrip("/") or "/"
        sensitive = any(path.startswith(prefix) for prefix in SENSITIVE_PREFIXES)
        write = request.method in {"POST", "PUT", "PATCH", "DELETE"}
        pii_read = request.method == "GET" and sensitive
        if not sensitive or not (write or pii_read):
            return response

        claims = getattr(request.state, "auth_claims", {})
        subject = claims.get("sub") if isinstance(claims, dict) else None
        try:
            user_id = int(subject) if subject is not None else None
        except (ValueError, TypeError):
            user_id = None

        parts = path.removeprefix("/api/v1/").split("/", 1)
        resource = parts[0][:50]
        action = "read" if pii_read else "write"
        client = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:255] or None
        duration_ms = (perf_counter() - started) * 1000
        session_factory = request.app.state.audit_session_factory
        async with session_factory() as db:
            try:
                db.add(
                    AuditLog(
                        user_id=user_id,
                        action=action,
                        resource=resource,
                        resource_id=path[:50],
                        method=request.method,
                        duration_ms=duration_ms,
                        ip_address=client,
                        user_agent=user_agent,
                        status=str(response.status_code),
                    )
                )
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("Audit log write failed for %s %s", request.method, path)
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Audit logging is unavailable."},
                )
        return response
