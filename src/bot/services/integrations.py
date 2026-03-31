"""Service functions for managing per-user channel integrations."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Integration

logger = logging.getLogger(__name__)

CHANNEL_EMAIL = "email"


async def get_integration(
    session: AsyncSession,
    user_id: uuid.UUID,
    channel: str,
) -> Integration | None:
    result = await session.execute(
        select(Integration).where(
            Integration.user_id == user_id,
            Integration.channel == channel,
        )
    )
    return result.scalar_one_or_none()


async def upsert_email_integration(
    session: AsyncSession,
    user_id: uuid.UUID,
    email: str,
) -> Integration:
    """Create or update the email integration for a user; always re-enables it."""
    integration = await get_integration(session, user_id, CHANNEL_EMAIL)
    if integration is None:
        integration = Integration(
            user_id=user_id,
            channel=CHANNEL_EMAIL,
            address=email,
            enabled=True,
        )
        session.add(integration)
        await session.flush()
        logger.info("Email integration created user_id=%s email=%s", user_id, email)
    else:
        integration.address = email
        integration.enabled = True
        integration.updated_at = datetime.now(UTC)
        logger.info("Email integration updated user_id=%s email=%s", user_id, email)
    return integration


async def disable_integration(
    session: AsyncSession,
    user_id: uuid.UUID,
    channel: str,
) -> bool:
    """Disable an integration. Returns True if it existed, False if not found."""
    integration = await get_integration(session, user_id, channel)
    if integration is None:
        return False
    integration.enabled = False
    integration.updated_at = datetime.now(UTC)
    logger.info("Integration disabled user_id=%s channel=%s", user_id, channel)
    return True


async def get_enabled_integrations(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[Integration]:
    """Return all enabled non-Telegram integrations for a user."""
    result = await session.execute(
        select(Integration).where(
            Integration.user_id == user_id,
            Integration.enabled == True,  # noqa: E712
        )
    )
    return list(result.scalars().all())
