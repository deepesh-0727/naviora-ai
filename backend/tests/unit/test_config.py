from app.core.config import Settings, settings
from app.main import get_cors_allowed_origins


def test_allowed_origins_accepts_comma_separated_environment_value():
    configured = Settings(
        SECRET_KEY="test-secret-key-naviora-ci-only-32",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        ENCRYPTION_KEY="test-encryption-key",
        ALLOWED_ORIGINS="https://api.naviora.ai, https://app.naviora.ai",
    )

    assert configured.ALLOWED_ORIGINS == ["https://api.naviora.ai", "https://app.naviora.ai"]


def test_cors_origins_merge_legacy_and_explicit_allowlists(monkeypatch):
    monkeypatch.setattr(settings, "BACKEND_CORS_ORIGINS", ["https://app.naviora.ai"])
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", ["https://api.naviora.ai", "https://app.naviora.ai"])

    assert get_cors_allowed_origins() == ["https://app.naviora.ai", "https://api.naviora.ai"]
