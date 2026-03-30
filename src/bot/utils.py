from datetime import date, datetime
from zoneinfo import ZoneInfo

from bot.config import settings


def get_timezone() -> ZoneInfo:
    return ZoneInfo(settings.bot_timezone)


def now_local() -> datetime:
    return datetime.now(tz=get_timezone())


def today_local() -> date:
    return now_local().date()


def get_cycle_key(d: date) -> str:
    """Return the cycle key for a given date, e.g. '2026-04'."""
    return d.strftime("%Y-%m")


def compute_due_date(due_day: int, reference: date) -> date:
    """Return the due date for the cycle containing `reference`.

    If the due day has already passed this month, return next month's due date.
    due_day is guaranteed to be 1–28 so no end-of-month clamping needed.
    """
    if reference.day <= due_day:
        return reference.replace(day=due_day)

    # Advance to next month
    if reference.month == 12:
        return date(reference.year + 1, 1, due_day)
    return date(reference.year, reference.month + 1, due_day)


def days_until(due: date, today: date) -> int:
    return (due - today).days


def format_amount(amount: float, currency: str) -> str:
    return f"{amount:,.2f} {currency}"


def format_due_date(d: date) -> str:
    return d.strftime("%d %b %Y")
