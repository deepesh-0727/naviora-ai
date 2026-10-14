import json
import logging
import re

from app.main import app
from app.core.logging import (
    JSONFormatter,
    RequestContextFilter,
    SecretRedactionFilter,
    formatter_for_environment,
    request_id_context,
    request_method_context,
    request_path_context,
    user_id_context,
)


def test_client_request_id_is_returned_and_logged(client, caplog):
    response = client.get("/health", headers={"X-Request-ID": "test-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-123"
    assert "test-123" in caplog.text


def test_missing_or_invalid_request_id_is_replaced_with_uuid(client):
    response = client.get("/health", headers={"X-Request-ID": "not/a-safe-id"})

    request_id = response.headers["X-Request-ID"]
    assert response.status_code == 200
    assert re.fullmatch(r"[0-9a-f-]{36}", request_id)


def test_unhandled_errors_still_return_request_id(client):
    async def fail_request():
        raise RuntimeError("internal failure")

    app.add_api_route("/_test/unhandled-error", fail_request, methods=["GET"])
    try:
        response = client.get("/_test/unhandled-error", headers={"X-Request-ID": "error-55"})
    finally:
        app.router.routes[:] = [
            route for route in app.router.routes
            if getattr(route, "path", None) != "/_test/unhandled-error"
        ]

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "error-55"


def test_json_logging_has_context_and_redacts_sensitive_values():
    tokens = [
        request_id_context.set("request-44"),
        user_id_context.set("user-7"),
        request_path_context.set("/api/v1/patients"),
        request_method_context.set("GET"),
    ]
    try:
        record = logging.LogRecord(
            "test.logger",
            logging.INFO,
            "test.py",
            1,
            {"password": "secret-value", "status": "ok"},
            (),
            None,
        )
        SecretRedactionFilter().filter(record)
        RequestContextFilter().filter(record)
        payload = json.loads(JSONFormatter().format(record))

        assert payload["timestamp"]
        assert payload["level"] == "INFO"
        assert payload["logger"] == "test.logger"
        assert payload["request_id"] == "request-44"
        assert payload["user_id"] == "user-7"
        assert payload["path"] == "/api/v1/patients"
        assert payload["method"] == "GET"
        assert "secret-value" not in payload["message"]
        assert "[REDACTED]" in payload["message"]
    finally:
        request_method_context.reset(tokens[3])
        request_path_context.reset(tokens[2])
        user_id_context.reset(tokens[1])
        request_id_context.reset(tokens[0])


def test_text_redaction_covers_secret_assignments_and_bearer_tokens():
    record = logging.LogRecord(
        "test.logger",
        logging.INFO,
        "test.py",
        1,
        "authorization: Bearer abc123 token=xyz password=swordfish",
        (),
        None,
    )
    SecretRedactionFilter().filter(record)
    rendered = JSONFormatter().format(record)

    assert "abc123" not in rendered
    assert "xyz" not in rendered
    assert "swordfish" not in rendered


def test_logging_formatter_depends_on_environment():
    assert isinstance(formatter_for_environment("prod"), JSONFormatter)
    assert not isinstance(formatter_for_environment("dev"), JSONFormatter)
