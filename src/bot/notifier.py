import logging
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from bot.channels.base import BaseChannel
from bot.services.payments import get_due_bills, log_reminder, reminder_already_sent
from bot.utils import format_amount, format_due_date

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChannelRoute:
    """Binds a channel name, its sender, and the recipient address together."""

    name: str  # e.g. 'telegram', 'email' — must match ReminderLog.channel values
    channel: BaseChannel
    recipient: str  # str(telegram_id) for Telegram, email address for Email


class _UserLike(Protocol):
    id: object
    telegram_id: int


async def notify_user(
    session: AsyncSession,
    user: _UserLike,
    routes: list[ChannelRoute],
) -> None:
    due = await get_due_bills(session, user.id)

    if not due:
        return

    for bill, due_date, days_left in due:
        for route in routes:
            already_sent = await reminder_already_sent(
                session, bill.id, due_date, route.name, days_left
            )
            if already_sent:
                logger.debug(
                    "Reminder already sent bill_id=%s channel=%s offset=%s",
                    bill.id,
                    route.name,
                    days_left,
                )
                continue

            text = _format_reminder(bill.name, bill.amount, bill.currency, due_date, days_left)
            try:
                await route.channel.send_message(route.recipient, text)
            except Exception:
                logger.exception("Failed to send via channel=%s bill_id=%s", route.name, bill.id)
                continue  # Don't log — will retry next run

            await log_reminder(session, bill.id, due_date, route.name, days_left)


def _format_reminder(
    name: str, amount: float, currency: str, due_date: object, days_left: int
) -> str:
    amount_str = format_amount(amount, currency)
    date_str = format_due_date(due_date)

    if days_left <= 0:
        return (
            f"⚠️ <b>{name}</b> was due on {date_str}\n"
            f"Amount: {amount_str}\n"
            f"Please mark it as paid with /paid"
        )
    if days_left == 1:
        return f"🔔 <b>{name}</b> is due <b>tomorrow</b> ({date_str})\nAmount: {amount_str}"
    return f"📅 <b>{name}</b> is due in <b>{days_left} days</b> ({date_str})\nAmount: {amount_str}"
