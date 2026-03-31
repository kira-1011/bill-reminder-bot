from abc import ABC, abstractmethod


class BaseChannel(ABC):
    @abstractmethod
    async def send_message(self, chat_id: int, text: str) -> None:
        """Send a plain-text message to the given chat."""
