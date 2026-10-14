import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry():
    if not settings.SENTRY_DSN:
        logger.warning("SENTRY_DSN not set — error tracking disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            integrations=[SqlalchemyIntegration()],
            environment=settings.ENVIRONMENT,
        )
        logger.info("Sentry initialized for environment %s", settings.ENVIRONMENT)
    except Exception:
        logger.exception("Sentry initialization failed; error tracking is unavailable")
