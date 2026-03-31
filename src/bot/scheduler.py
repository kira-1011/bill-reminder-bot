import logging
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import select
from telegram.ext import Application

from bot.channels.email import EmailChannel
from bot.channels.telegram import TelegramChannel
from bot.config import settings
from bot.db.connection import get_session
from bot.db.models import User
from bot.notifier import ChannelRoute, notify_user
from bot.services.integrations import get_enabled_integrations

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _UserRef:
    id: object
    telegram_id: int


async def daily_check(context: object) -> None:
    """Run once daily — send reminders for all users via all enabled channels."""
    logger.info("Daily check started")

    bot = context.bot
    telegram_channel = TelegramChannel(bot)
    email_channel = EmailChannel()

    async with get_session() as session:
        result = await session.execute(select(User.id, User.telegram_id))
        users = [_UserRef(id=row.id, telegram_id=row.telegram_id) for row in result]

    for user in users:
        try:
            async with get_session() as session:
                integrations = await get_enabled_integrations(session, user.id)
                routes = _build_routes(user, telegram_channel, email_channel, integrations)
                await notify_user(session, user, routes)
        except Exception:
            logger.exception("Failed to notify user telegram_id=%s", user.telegram_id)

    logger.info("Daily check finished users=%d", len(users))


def _build_routes(
    user: _UserRef,
    telegram_channel: TelegramChannel,
    email_channel: EmailChannel,
    integrations: list,
) -> list[ChannelRoute]:
    """Always include Telegram; append email route if the integration is enabled."""
    routes: list[ChannelRoute] = [
        ChannelRoute(
            name="telegram",
            channel=telegram_channel,
            recipient=str(user.telegram_id),
        )
    ]
    for integration in integrations:
        if integration.channel == "email":
            routes.append(
                ChannelRoute(
                    name="email",
                    channel=email_channel,
                    recipient=integration.address,
                )
            )
    return routes


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
