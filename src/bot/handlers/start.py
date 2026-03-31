import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.db.connection import get_session
from bot.services.bills import upsert_user

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with get_session() as session:
        await upsert_user(session, tg_user.id, tg_user.username)

    logger.info("User started bot telegram_id=%s", tg_user.id)
    await update.message.reply_text(
        "👋 Welcome to <b>Bill Reminder Bot</b>!\n\n"
        "Commands:\n"
        "/addbill — add a new bill\n"
        "/bills — list your bills\n"
        "/delbill — delete a bill\n"
        "/paid — mark a bill as paid\n"
        "/history — payment history",
        parse_mode="HTML",
    )
