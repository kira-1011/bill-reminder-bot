import asyncio
import logging

from alembic import command
from alembic.config import Config

from bot.config import settings, setup_logging
from bot.db.connection import close_db, engine

logger = logging.getLogger(__name__)


async def run_migrations() -> None:
    alembic_cfg = Config("pyproject.toml", ini_section="tool.alembic")
    async with engine.begin() as conn:
        await conn.run_sync(_upgrade, alembic_cfg)
    logger.info("Migrations applied")


def _upgrade(connection: object, alembic_cfg: Config) -> None:
    alembic_cfg.attributes["connection"] = connection
    command.upgrade(alembic_cfg, "head")


def main() -> None:
    setup_logging(settings.log_level)
    logger.info("Bot starting")

    asyncio.run(_main())


async def _main() -> None:
    await run_migrations()

    from bot.bot import build_application

    application = build_application()
    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("Bot is polling")
        # Block until stopped
        await application.updater.idle()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await close_db()
        logger.info("Bot shut down cleanly")


if __name__ == "__main__":
    main()
