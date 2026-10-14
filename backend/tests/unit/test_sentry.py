import logging
import sys
from types import ModuleType
from unittest.mock import Mock

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
