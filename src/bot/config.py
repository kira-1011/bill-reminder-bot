import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str
    database_url: str
    bot_timezone: str = "Etc/GMT-3"
    log_level: str = "INFO"
    resend_api_key: str = ""
    resend_from_address: str = "reminders@bill-bot.example"


def setup_logging(level: str) -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=level.upper(),
    )
    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


settings = Settings()
