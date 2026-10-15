import logging
import sys
from types import ModuleType
from unittest.mock import Mock

import sentry_sdk
from sentry_sdk.transport import Transport

from app.core import sentry


def test_sentry_is_disabled_with_clear_warning(monkeypatch, caplog):
    monkeypatch.setattr(sentry.settings, "SENTRY_DSN", "")

    with caplog.at_level(logging.WARNING, logger="app.core.sentry"):
        sentry.init_sentry()

    assert "SENTRY_DSN not set — error tracking disabled" in caplog.text


def test_sentry_uses_configured_dsn_and_environment(monkeypatch):
    sdk = ModuleType("sentry_sdk")
    sdk.init = Mock()
    integrations = ModuleType("sentry_sdk.integrations")
    sqlalchemy = ModuleType("sentry_sdk.integrations.sqlalchemy")
    sqlalchemy.SqlalchemyIntegration = Mock(return_value="sqlalchemy-integration")
    monkeypatch.setitem(sys.modules, "sentry_sdk", sdk)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations", integrations)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.sqlalchemy", sqlalchemy)
    monkeypatch.setattr(sentry.settings, "SENTRY_DSN", "https://public@example.invalid/1")
    monkeypatch.setattr(sentry.settings, "ENVIRONMENT", "staging")

    sentry.init_sentry()

    sdk.init.assert_called_once_with(
        dsn="https://public@example.invalid/1",
        traces_sample_rate=0.1,
        integrations=["sqlalchemy-integration"],
        environment="staging",
    )


def test_sentry_initializes_and_captures_exception_with_test_transport(monkeypatch):
    captured_envelopes = []

    class RecordingTransport(Transport):
        def capture_envelope(self, envelope):
            captured_envelopes.append(envelope)

    monkeypatch.setattr(sentry.settings, "SENTRY_DSN", "https://public@example.invalid/1")
    monkeypatch.setattr(sentry.settings, "ENVIRONMENT", "test")

    try:
        assert sentry.init_sentry(transport=RecordingTransport)
        sentry_sdk.capture_exception(ValueError("Sentry transport verification"))
        sentry_sdk.flush(timeout=2)
        assert captured_envelopes
        assert any(
            item.type == "event"
            and "Sentry transport verification" in str(item.payload.json)
            for envelope in captured_envelopes
            for item in envelope
        )
    finally:
        sentry_sdk.flush(timeout=2)
        sentry_sdk.init(dsn=None)
