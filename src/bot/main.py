import logging

from alembic import command
from alembic.config import Config

from bot.config import settings, setup_logging

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations applied")


def main() -> None:
    setup_logging(settings.log_level)
    logger.info("Bot starting")
    run_migrations()

    from bot.bot import build_application

    application = build_application()
    logger.info("Bot is polling")
    application.run_polling()
    logger.info("Bot shut down cleanly")


if __name__ == "__main__":
    main()
