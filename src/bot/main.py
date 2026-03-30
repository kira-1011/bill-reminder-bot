import logging

from bot.config import settings, setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging(settings.log_level)
    logger.info("Bot starting — not fully implemented yet")


if __name__ == "__main__":
    main()
