import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Bill, Payment, ReminderLog
from bot.utils import compute_due_date, get_cycle_key, today_local

logger = logging.getLogger(__name__)


async def get_or_create_payment(
    session: AsyncSession,
    bill: Bill,
    cycle_key: str,
    due_date: date,
) -> Payment:
    result = await session.execute(
        select(Payment).where(Payment.bill_id == bill.id, Payment.cycle_key == cycle_key)
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        payment = Payment(
            bill_id=bill.id,
            user_id=bill.user_id,
            cycle_key=cycle_key,
            due_date=due_date,
            status="pending",
        )
        session.add(payment)
        await session.flush()
    return payment


async def mark_paid(
    session: AsyncSession,
    bill: Bill,
    cycle_key: str,
    due_date: date,
    paid_amount: float | None = None,
) -> Payment:
    payment = await get_or_create_payment(session, bill, cycle_key, due_date)
    payment.status = "paid"
    payment.paid_date = today_local()
    if paid_amount is not None:
        payment.amount = paid_amount
    logger.info("Payment marked paid bill_id=%s cycle=%s", bill.id, cycle_key)
    return payment


async def get_due_bills(session: AsyncSession, user_id: uuid.UUID) -> list[tuple[Bill, date, int]]:
    """Return (bill, due_date, days_left) for enabled bills with a reminder due today."""
    today = today_local()
    result = await session.execute(
        select(Bill).where(Bill.user_id == user_id, Bill.enabled == True)  # noqa: E712
    )
    bills = list(result.scalars().all())

    due = []
    for bill in bills:
        due_date = compute_due_date(bill.due_day, today)
        days_left = (due_date - today).days
        if days_left in bill.reminder_days or days_left <= 0:
            due.append((bill, due_date, days_left))
    return due


async def reminder_already_sent(
    session: AsyncSession,
    bill_id: uuid.UUID,
    due_date: date,
    channel: str,
    offset_days: int,
) -> bool:
    result = await session.execute(
        select(ReminderLog).where(
            ReminderLog.bill_id == bill_id,
            ReminderLog.due_date == due_date,
            ReminderLog.channel == channel,
            ReminderLog.offset_days == offset_days,
        )
    )
    return result.scalar_one_or_none() is not None


async def log_reminder(
    session: AsyncSession,
    bill_id: uuid.UUID,
    due_date: date,
    channel: str,
    offset_days: int,
) -> None:
    session.add(
        ReminderLog(
            bill_id=bill_id,
            due_date=due_date,
            channel=channel,
            offset_days=offset_days,
        )
    )
    logger.info(
        "Reminder logged bill_id=%s due=%s channel=%s offset=%sd",
        bill_id,
        due_date,
        channel,
        offset_days,
    )


async def get_history(session: AsyncSession, user_id: uuid.UUID, months: int = 6) -> list[Payment]:
    today = today_local()
    year = today.year
    month = today.month - months
    while month <= 0:
        month += 12
        year -= 1
    cutoff_key = get_cycle_key(date(year, month, 1))

    result = await session.execute(
        select(Payment)
        .join(Bill, Payment.bill_id == Bill.id)
        .where(Bill.user_id == user_id, Payment.cycle_key >= cutoff_key)
        .order_by(Payment.due_date.desc())
    )
    return list(result.scalars().all())
