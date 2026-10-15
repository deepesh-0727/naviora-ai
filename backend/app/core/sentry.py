import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry(*, transport=None):
    if not settings.SENTRY_DSN:
        logger.warning("SENTRY_DSN not set — error tracking disabled")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        options = dict(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            integrations=[SqlalchemyIntegration()],
            environment=settings.ENVIRONMENT,
        )
        if transport is not None:
            options["transport"] = transport
        sentry_sdk.init(**options)
        logger.info("Sentry initialized for environment %s", settings.ENVIRONMENT)
        return sentry_sdk.get_client().is_active()
    except Exception:
        logger.exception("Sentry initialization failed; error tracking is unavailable")
        return False
