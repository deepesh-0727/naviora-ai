import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BeforeValidator, model_validator
from typing_extensions import Annotated


def any_http_url_list_validator(v: str | List[str]) -> List[str]:
    if isinstance(v, str):
        if not v:
            return []
        return [item.strip() for item in v.split(",")]
    return v


class Settings(BaseSettings):
    PROJECT_NAME: str = "Naviora AI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440   # 24 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080 # 7 days

    # CORS origins
    BACKEND_CORS_ORIGINS: Annotated[
        List[str], BeforeValidator(any_http_url_list_validator)
    ] = []

    # =========================================================
    # DATABASE — Supabase Session Pooler (IPv4 compatible)
    # Uses asyncpg driver for FastAPI + Alembic async engine
    # =========================================================
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Supabase specific keys
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # =========================================================
    # Redis
    # =========================================================
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL: int = 3600
    CACHE_ENABLED: bool = True
    CACHE_PREFIX: str = "naviora:intent:"

    # =========================================================
    # Notification providers
    # =========================================================
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")
    TEXTLOCAL_API_KEY: str = os.getenv("SMS_API_KEY", "")
    SMS_SENDER: str = "NAVIORA"
    TWILIO_SID: str = os.getenv("TWILIO_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    EMAIL_API_KEY: str = os.getenv("EMAIL_API_KEY", "")
    SENDGRID_API_KEY: str = os.getenv("EMAIL_API_KEY", "")
    EMAIL_FROM: str = "noreply@naviora.ai"
    FIREBASE_CREDENTIALS: str = os.getenv("FIREBASE_CREDENTIALS", "")

    # =========================================================
    # Payment Gateway
    # =========================================================
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

    # =========================================================
    # RabbitMQ / Celery
    # =========================================================
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"

    # =========================================================
    # Security
    # =========================================================
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    ALLOWED_HOSTS: List[str] = [
        "naviora-backend.onrender.com",
        "naviora-backend-s6je.onrender.com",
        "naviora-api.onrender.com",
        "localhost",
        "127.0.0.1",
    ]

    # =========================================================
    # AI Model Endpoints
    # =========================================================
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "ollama")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4_K_M")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    WHISPER_API_URL: str = "http://localhost:8000/stt"
    PIPER_API_URL: str = "http://localhost:8000/tts"

    # AI Control Parameters
    AI_TEMPERATURE: float = 0.2
    AI_REQUEST_TIMEOUT: float = 30.0
    AI_MAX_RETRIES: int = 3
    AI_BACKOFF_FACTOR: float = 2.0

    # =========================================================
    # Database Pool Settings
    # =========================================================
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # =========================================================
    # Monitoring
    # =========================================================
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters.")
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL must be configured.")
        if not self.ENCRYPTION_KEY:
            raise ValueError("ENCRYPTION_KEY must be configured for patient PII encryption.")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
