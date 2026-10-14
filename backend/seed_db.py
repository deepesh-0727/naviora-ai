"""Legacy entry point retained for deployments; applies schema migrations only."""
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


def upgrade_schema() -> None:
    """Apply Alembic schema changes without inserting synthetic records."""
    config = Config(str(Path(__file__).with_name("alembic.ini")))
    command.upgrade(config, "head")
    logger.info("Database schema is at the latest Alembic revision.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    upgrade_schema()
