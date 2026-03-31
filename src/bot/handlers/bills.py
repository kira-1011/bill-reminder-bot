import logging
import uuid

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
from bot.services.bills import (
    add_bill,
    delete_bill,
    get_user_by_telegram_id,
    list_bills,
)
from bot.utils import format_amount

logger = logging.getLogger(__name__)

# ConversationHandler states
ASK_NAME, ASK_AMOUNT, ASK_CURRENCY, ASK_DUE_DAY = range(4)


async def addbill_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("What is the name of the bill? (e.g. Netflix, Rent)")
    return ASK_NAME


async def addbill_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("How much is it? (e.g. 9.99)")
    return ASK_AMOUNT


async def addbill_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = float(update.message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid positive number (e.g. 9.99)")
        return ASK_AMOUNT

    context.user_data["amount"] = amount
    await update.message.reply_text("What currency? (e.g. USD, EUR, GBP) — or send /skip for USD")
    return ASK_CURRENCY


async def addbill_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["currency"] = update.message.text.strip().upper()
    await update.message.reply_text("Which day of the month is it due? (1–28)")
    return ASK_DUE_DAY


async def addbill_currency_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["currency"] = "USD"
    await update.message.reply_text("Which day of the month is it due? (1–28)")
    return ASK_DUE_DAY


async def addbill_due_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        due_day = int(update.message.text.strip())
        if not 1 <= due_day <= 28:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a number between 1 and 28")
        return ASK_DUE_DAY

    tg_user = update.effective_user
    name = context.user_data["name"]
    amount = context.user_data["amount"]
    currency = context.user_data["currency"]

    async with get_session() as session:
        user = await get_user_by_telegram_id(session, tg_user.id)
        if user is None:
            await update.message.reply_text("Please run /start first.")
            return ConversationHandler.END
        await add_bill(session, user.id, name, amount, currency, due_day)

    await update.message.reply_text(
        f"✅ <b>{name}</b> added — {format_amount(amount, currency)} due on day {due_day}",
        parse_mode="HTML",
    )
    context.user_data.clear()
    return ConversationHandler.END


async def addbill_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def bills_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with get_session() as session:
        user = await get_user_by_telegram_id(session, tg_user.id)
        if user is None:
            await update.message.reply_text("Please run /start first.")
            return
        bills = await list_bills(session, user.id)

    if not bills:
        await update.message.reply_text("You have no bills. Use /addbill to add one.")
        return

    lines = ["<b>Your bills:</b>\n"]
    for b in bills:
        lines.append(
            f"• <b>{b.name}</b> — {format_amount(b.amount, b.currency)} on day {b.due_day}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def delbill_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with get_session() as session:
        user = await get_user_by_telegram_id(session, tg_user.id)
        if user is None:
            await update.message.reply_text("Please run /start first.")
            return
        bills = await list_bills(session, user.id)

    if not bills:
        await update.message.reply_text("You have no bills to delete.")
        return

    keyboard = [[InlineKeyboardButton(b.name, callback_data=f"delbill:{b.id}")] for b in bills]
    await update.message.reply_text(
        "Select a bill to delete:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def delbill_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    bill_id = uuid.UUID(query.data.split(":")[1])
    tg_user = update.effective_user

    async with get_session() as session:
        user = await get_user_by_telegram_id(session, tg_user.id)
        if user is None:
            await query.edit_message_text("Please run /start first.")
            return
        deleted = await delete_bill(session, user.id, bill_id)

    if deleted:
        await query.edit_message_text("✅ Bill deleted.")
    else:
        await query.edit_message_text("Bill not found.")


def build_addbill_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("addbill", addbill_start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addbill_name)],
            ASK_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, addbill_amount)],
            ASK_CURRENCY: [
                CommandHandler("skip", addbill_currency_skip),
                MessageHandler(filters.TEXT & ~filters.COMMAND, addbill_currency),
            ],
            ASK_DUE_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, addbill_due_day)],
        },
        fallbacks=[CommandHandler("cancel", addbill_cancel)],
        conversation_timeout=300,
    )


def build_delbill_handler() -> CallbackQueryHandler:
    return CallbackQueryHandler(delbill_confirm, pattern=r"^delbill:")
