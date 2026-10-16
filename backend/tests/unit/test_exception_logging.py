import logging

import pytest
from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError

from app.core import exceptions


@pytest.mark.asyncio
async def test_sqlalchemy_handler_logs_traceback_and_keeps_response_generic(caplog, monkeypatch):
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/register",
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
        }
    )
    exception = SQLAlchemyError("sensitive database detail")
    capture_exception = []
    monkeypatch.setattr(exceptions.sentry_sdk, "capture_exception", capture_exception.append)

    with caplog.at_level(logging.ERROR):
        try:
            raise exception
        except SQLAlchemyError as error:
            response = await exceptions.sqlalchemy_exception_handler(request, error)

    assert response.status_code == 500
    assert b"sensitive database detail" not in response.body
    assert "SQLAlchemyError: sensitive database detail" in caplog.text
    assert "Traceback (most recent call last)" in caplog.text
    assert capture_exception == [exception]
