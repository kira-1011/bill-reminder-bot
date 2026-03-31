import logging
from collections import defaultdict

from telegram import Update
from telegram.ext import ContextTypes

from bot.db.connection import get_session
from bot.services.bills import get_user_by_telegram_id
from bot.services.payments import get_history
from bot.utils import format_amount

logger = logging.getLogger(__name__)


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with get_session() as session:
        user = await get_user_by_telegram_id(session, tg_user.id)
        if user is None:
            await update.message.reply_text("Please run /start first.")
            return
        payments = await get_history(session, user.id)

    if not payments:
        await update.message.reply_text("No payment history found.")
        return

    # Group by cycle_key (YYYY-MM) descending
    by_cycle: dict[str, list] = defaultdict(list)
    for p in payments:
        by_cycle[p.cycle_key].append(p)

    lines = ["<b>Payment history (last 6 months):</b>\n"]
    for cycle in sorted(by_cycle.keys(), reverse=True):
        lines.append(f"\n<b>{cycle}</b>")
        for p in by_cycle[cycle]:
            status_icon = "✅" if p.status == "paid" else "⏳" if p.status == "pending" else "❌"
            amount_str = format_amount(p.amount or 0, "")
            lines.append(f"  {status_icon} {amount_str} — due {p.due_date}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
