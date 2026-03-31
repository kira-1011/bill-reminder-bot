"""Email delivery channel via the Resend Python SDK."""

import logging

import resend

from bot.channels.base import BaseChannel
from bot.config import settings

logger = logging.getLogger(__name__)

_EMAIL_SUBJECT = "Bill Reminder"


class EmailChannel(BaseChannel):
    def __init__(self) -> None:
        resend.api_key = settings.resend_api_key

    async def send_message(self, recipient: str, text: str) -> None:
        params: resend.Emails.SendParams = {
            "from": settings.resend_from_address,
            "to": [recipient],
            "subject": _EMAIL_SUBJECT,
            "html": text,
        }
        result = resend.Emails.send(params)
        logger.debug("Email sent id=%s to=%s", result.get("id"), recipient)
