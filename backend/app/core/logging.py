"""Environment-aware logging with request context and secret redaction."""

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_context: ContextVar[str | None] = ContextVar("user_id", default=None)
request_path_context: ContextVar[str | None] = ContextVar("request_path", default=None)
request_method_context: ContextVar[str | None] = ContextVar("request_method", default=None)

_SENSITIVE_NAMES = {"password", "token", "secret", "api_key", "authorization"}
_SECRET_PAIR = re.compile(
    r"(?i)(password|token|secret|api[_-]?key|authorization)(\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|Bearer\s+[^\s,;]+|[^\s,;]+)"
)
_BEARER_SECRET = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")


def _is_sensitive_name(name: object) -> bool:
    normalized = str(name).lower().replace("-", "_")
    return any(normalized == key or normalized.endswith(f"_{key}") for key in _SENSITIVE_NAMES)


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _is_sensitive_name(key) else _redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_text(value: str) -> str:
    value = _SECRET_PAIR.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", value)
    return _BEARER_SECRET.sub("Bearer [REDACTED]", value)


class SecretRedactionFilter(logging.Filter):
    """Redact common credential keys in structured and interpolated log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, dict):
            record.msg = json.dumps(_redact_value(record.msg), default=str)
        elif isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        record.args = _redact_value(record.args)
        if record.exc_text:
            record.exc_text = redact_text(record.exc_text)
        return True


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get() or ""
        record.user_id = user_id_context.get() or ""
        record.path = request_path_context.get() or ""
        record.method = request_method_context.get() or ""
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
            "request_id": getattr(record, "request_id", ""),
            "user_id": getattr(record, "user_id", ""),
            "path": getattr(record, "path", ""),
            "method": getattr(record, "method", ""),
        }
        if record.exc_info:
            log_data["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(log_data, ensure_ascii=False, default=str)


def formatter_for_environment(environment: str) -> logging.Formatter:
    if environment.lower() == "prod":
        return JSONFormatter()
    return logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s "
        "request_id=%(request_id)s user_id=%(user_id)s path=%(path)s method=%(method)s"
    )


def setup_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.addFilter(SecretRedactionFilter())
    stream_handler.addFilter(RequestContextFilter())
    stream_handler.setFormatter(formatter_for_environment(settings.ENVIRONMENT))
    root_logger.addHandler(stream_handler)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
