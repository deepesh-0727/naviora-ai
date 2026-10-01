import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry():
    if not settings.SENTRY_DSN:
        logger.info("Sentry DSN not configured. Sentry tracking is disabled.")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.2,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            environment=settings.PROJECT_NAME
        )
        logger.info("Sentry initialized successfully.")
    except Exception as exc:
        logger.warning(f"Failed to initialize Sentry SDK: {exc}")
