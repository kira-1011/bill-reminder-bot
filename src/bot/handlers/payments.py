import logging
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from bot.db.connection import get_session
from bot.services.bills import get_bill, get_user_by_telegram_id, list_bills
from bot.services.payments import mark_paid
from bot.utils import compute_due_date, format_amount, get_cycle_key, today_local

logger = logging.getLogger(__name__)


async def paid_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    keyboard = [
        [
            InlineKeyboardButton(
                f"{b.name} — {format_amount(b.amount, b.currency)}",
                callback_data=f"paid:{b.id}",
            )
        ]
        for b in bills
    ]
    await update.message.reply_text(
        "Which bill did you pay?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def paid_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    bill_id = uuid.UUID(query.data.split(":")[1])
    tg_user = update.effective_user
    today = today_local()

    async with get_session() as session:
        user = await get_user_by_telegram_id(session, tg_user.id)
        if user is None:
            await query.edit_message_text("Please run /start first.")
            return

        bill = await get_bill(session, user.id, bill_id)
        if bill is None:
            await query.edit_message_text("Bill not found.")
            return

        due_date = compute_due_date(bill.due_day, today)
        cycle_key = get_cycle_key(due_date)
        await mark_paid(session, bill, cycle_key, due_date)

    logger.info("Bill marked paid bill_id=%s cycle=%s", bill_id, cycle_key)
    await query.edit_message_text(f"✅ <b>{bill.name}</b> marked as paid!", parse_mode="HTML")


def build_paid_handler() -> CallbackQueryHandler:
    return CallbackQueryHandler(paid_confirm, pattern=r"^paid:")
