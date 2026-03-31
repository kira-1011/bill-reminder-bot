"""Handler for /settings — lets users view and manage their email integration."""

import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.db.connection import get_session
from bot.db.models import Integration
from bot.services.bills import get_user_by_telegram_id
from bot.services.integrations import (
    CHANNEL_EMAIL,
    disable_integration,
    get_integration,
    upsert_email_integration,
)

logger = logging.getLogger(__name__)

SHOW_MENU, ASK_EMAIL = range(2)

_CB_SET_EMAIL = "settings:set_email"
_CB_DISABLE_EMAIL = "settings:disable_email"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def settings_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tg_user = update.effective_user
    async with get_session() as session:
        user = await get_user_by_telegram_id(session, tg_user.id)
        if user is None:
            await update.message.reply_text("Please run /start first.")
            return ConversationHandler.END

        integration = await get_integration(session, user.id, CHANNEL_EMAIL)

    text, keyboard = _build_settings_menu(integration)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    return SHOW_MENU


def _build_settings_menu(
    integration: Integration | None,
) -> tuple[str, InlineKeyboardMarkup]:
    if integration is None or not integration.enabled:
        status_line = "Email reminders: <b>OFF</b>"
        buttons = [[InlineKeyboardButton("Set email address", callback_data=_CB_SET_EMAIL)]]
    else:
        status_line = f"Email reminders: <b>ON</b> ({integration.address})"
        buttons = [
            [InlineKeyboardButton("Change email address", callback_data=_CB_SET_EMAIL)],
            [InlineKeyboardButton("Disable email reminders", callback_data=_CB_DISABLE_EMAIL)],
        ]

    text = f"<b>Notification Settings</b>\n\nTelegram reminders: <b>always ON</b>\n{status_line}"
    return text, InlineKeyboardMarkup(buttons)


async def settings_set_email_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please send me your email address:")
    return ASK_EMAIL


async def settings_receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text.strip()

    if not _EMAIL_RE.match(email):
        await update.message.reply_text(
            "That doesn't look like a valid email. Please try again, or /cancel:"
        )
        return ASK_EMAIL

    tg_user = update.effective_user
    async with get_session() as session:
        user = await get_user_by_telegram_id(session, tg_user.id)
        if user is None:
            await update.message.reply_text("Please run /start first.")
            return ConversationHandler.END
        await upsert_email_integration(session, user.id, email)

    await update.message.reply_text(
        f"✅ Email reminders enabled for <b>{email}</b>", parse_mode="HTML"
    )
    return ConversationHandler.END


async def settings_disable_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    tg_user = update.effective_user
    async with get_session() as session:
        user = await get_user_by_telegram_id(session, tg_user.id)
        if user is None:
            await query.edit_message_text("Please run /start first.")
            return ConversationHandler.END
        await disable_integration(session, user.id, CHANNEL_EMAIL)

    await query.edit_message_text("Email reminders <b>disabled</b>.", parse_mode="HTML")
    return ConversationHandler.END


async def settings_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def build_settings_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("settings", settings_start)],
        states={
            SHOW_MENU: [
                CallbackQueryHandler(settings_set_email_prompt, pattern=r"^settings:set_email$"),
                CallbackQueryHandler(settings_disable_email, pattern=r"^settings:disable_email$"),
            ],
            ASK_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings_receive_email),
            ],
        },
        fallbacks=[CommandHandler("cancel", settings_cancel)],
        conversation_timeout=300,
    )
