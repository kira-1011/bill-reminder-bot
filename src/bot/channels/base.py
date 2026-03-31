from abc import ABC, abstractmethod


class BaseChannel(ABC):
    @abstractmethod
    async def send_message(self, recipient: str, text: str) -> None:
        """Send a message to the recipient.

        For Telegram: recipient is str(telegram_id).
        For Email: recipient is the email address.
        """
