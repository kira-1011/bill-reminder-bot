"""Unit tests for bot.services.integrations."""

import uuid

import pytest

from bot.db.models import Integration
from bot.services.integrations import (
    CHANNEL_EMAIL,
    disable_integration,
    get_enabled_integrations,
    get_integration,
    upsert_email_integration,
)

from .helpers import make_session


def _make_integration(user_id: uuid.UUID, *, enabled: bool = True) -> Integration:
    return Integration(
        id=uuid.uuid4(),
        user_id=user_id,
        channel=CHANNEL_EMAIL,
        address="alice@example.com",
        enabled=enabled,
    )


@pytest.mark.unit
class TestGetIntegration:
    async def test_returns_none_when_not_found(self, user_id):
        session = make_session(scalar=None)
        result = await get_integration(session, user_id, CHANNEL_EMAIL)
        assert result is None

    async def test_returns_integration_when_found(self, user_id):
        integration = _make_integration(user_id)
        session = make_session(scalar=integration)
        result = await get_integration(session, user_id, CHANNEL_EMAIL)
        assert result is integration


@pytest.mark.unit
class TestUpsertEmailIntegration:
    async def test_creates_new_integration_when_not_found(self, user_id):
        session = make_session(scalar=None)
        result = await upsert_email_integration(session, user_id, "new@example.com")
        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert result.address == "new@example.com"
        assert result.enabled is True
        assert result.channel == CHANNEL_EMAIL

    async def test_updates_address_when_integration_exists(self, user_id):
        existing = _make_integration(user_id)
        existing.address = "old@example.com"
        existing.enabled = False
        session = make_session(scalar=existing)
        result = await upsert_email_integration(session, user_id, "new@example.com")
        session.add.assert_not_called()
        assert result.address == "new@example.com"
        assert result.enabled is True

    async def test_re_enables_disabled_integration(self, user_id):
        existing = _make_integration(user_id, enabled=False)
        session = make_session(scalar=existing)
        result = await upsert_email_integration(session, user_id, existing.address)
        assert result.enabled is True


@pytest.mark.unit
class TestDisableIntegration:
    async def test_returns_false_when_not_found(self, user_id):
        session = make_session(scalar=None)
        result = await disable_integration(session, user_id, CHANNEL_EMAIL)
        assert result is False

    async def test_returns_true_and_disables_when_found(self, user_id):
        integration = _make_integration(user_id, enabled=True)
        session = make_session(scalar=integration)
        result = await disable_integration(session, user_id, CHANNEL_EMAIL)
        assert result is True
        assert integration.enabled is False


@pytest.mark.unit
class TestGetEnabledIntegrations:
    async def test_returns_empty_when_none(self, user_id):
        session = make_session(scalars=[])
        result = await get_enabled_integrations(session, user_id)
        assert result == []

    async def test_returns_enabled_integrations(self, user_id):
        integration = _make_integration(user_id, enabled=True)
        session = make_session(scalars=[integration])
        result = await get_enabled_integrations(session, user_id)
        assert result == [integration]
