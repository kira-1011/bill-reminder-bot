import logging
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import select
from telegram.ext import Application

from bot.channels.telegram import TelegramChannel
from bot.config import settings
from bot.db.connection import get_session
from bot.db.models import User
from bot.notifier import notify_user

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _UserRef:
    id: object
    telegram_id: int


async def daily_check(context: object) -> None:
    """Run once daily — send reminders for all users with bills due."""
    logger.info("Daily check started")

    bot = context.bot
    channel = TelegramChannel(bot)

    async with get_session() as session:
        result = await session.execute(select(User.id, User.telegram_id))
        users = [_UserRef(id=row.id, telegram_id=row.telegram_id) for row in result]

    for user in users:
        try:
            async with get_session() as session:
                await notify_user(session, user, channel)
        except Exception:
            logger.exception("Failed to notify user telegram_id=%s", user.telegram_id)

    logger.info("Daily check finished users=%d", len(users))


def register_scheduler(application: Application) -> None:
    tz = ZoneInfo(settings.bot_timezone)
    application.job_queue.run_daily(
        daily_check,
        time=_parse_time("09:00", tz),
        name="daily_check",
    )
    logger.info("Scheduler registered daily_check at 09:00 %s", settings.bot_timezone)


def _parse_time(time_str: str, tz: ZoneInfo) -> object:
    from datetime import time

    hour, minute = map(int, time_str.split(":"))
    return time(hour, minute, tzinfo=tz)
