"""Propagate a safe request ID through application logs and responses."""

import re
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.responses import JSONResponse
import logging

from app.core.logging import (
    request_id_context,
    request_method_context,
    request_path_context,
    user_id_context,
)

logger = logging.getLogger(__name__)
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        supplied_id = request.headers.get("X-Request-ID", "")
        request_id = supplied_id if _VALID_REQUEST_ID.fullmatch(supplied_id) else str(uuid.uuid4())
        request.state.request_id = request_id
        request_id_token = request_id_context.set(request_id)
        user_id_token = user_id_context.set(None)
        path_token = request_path_context.set(request.url.path)
        method_token = request_method_context.set(request.method)
        try:
            try:
                response = await call_next(request)
            except Exception:
                logger.exception("Unhandled request exception")
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Internal server error.", "request_id": request_id},
                )
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_method_context.reset(method_token)
            request_path_context.reset(path_token)
            user_id_context.reset(user_id_token)
            request_id_context.reset(request_id_token)
