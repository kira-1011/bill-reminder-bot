import logging

from telegram import Bot

from bot.channels.base import BaseChannel

logger = logging.getLogger(__name__)


class TelegramChannel(BaseChannel):
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_message(self, recipient: str, text: str) -> None:
        await self._bot.send_message(chat_id=int(recipient), text=text, parse_mode="HTML")
        logger.debug("Telegram message sent chat_id=%s", recipient)
