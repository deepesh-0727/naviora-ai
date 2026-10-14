import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

class EnterpriseMiddleware(BaseHTTPMiddleware):
    """
    Enterprise-grade middleware for:
    1. Request ID Generation (Traceability)
    2. Request Timing (Performance Monitoring)
    3. Security Headers (Compliance)
    4. Structured Logging
    """
    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", "unknown")

        start_time = time.time()

        # Log incoming request
        logger.info(
            "Incoming Request: %s %s [RID: %s] client=%s",
            request.method,
            request.url.path,
            request_id,
            request.client.host if request.client else "unknown",
        )

        try:
            response: Response = await call_next(request)
        except Exception:
            logger.exception("Unhandled request exception [RID: %s]", request_id)
            raise

        process_time = (time.time() - start_time) * 1000

        # Add tracking and security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-MS"] = f"{process_time:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"

        # Enterprise CSP: Allow 'self' but also the CDNs required for Swagger UI
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "img-src 'self' data: fastly.jsdelivr.net; "
            "connect-src 'self'"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        logger.info(
            "Completed Request: %s %s [RID: %s] status=%s time=%.2fms",
            request.method,
            request.url.path,
            request_id,
            response.status_code,
            process_time,
        )

        return response
