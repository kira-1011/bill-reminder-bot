import logging

from telegram.ext import Application, ApplicationBuilder, CommandHandler

from bot.config import settings
from bot.handlers.bills import (
    bills_list,
    build_addbill_handler,
    build_delbill_handler,
    delbill_start,
)
from bot.handlers.errors import error_handler
from bot.handlers.history import history
from bot.handlers.payments import build_paid_handler, paid_start
from bot.handlers.start import start
from bot.scheduler import register_scheduler

logger = logging.getLogger(__name__)


def build_application() -> Application:
    application = ApplicationBuilder().token(settings.telegram_bot_token).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bills", bills_list))
    application.add_handler(CommandHandler("delbill", delbill_start))
    application.add_handler(CommandHandler("paid", paid_start))
    application.add_handler(CommandHandler("history", history))

    # ConversationHandler for /addbill
    application.add_handler(build_addbill_handler())

    # Inline keyboard callbacks
    application.add_handler(build_delbill_handler())
    application.add_handler(build_paid_handler())

    # Daily scheduler
    register_scheduler(application)

    # Global error handler
    application.add_error_handler(error_handler)

    logger.info("Application built with all handlers registered")
    return application
