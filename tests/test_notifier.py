"""Unit tests for bot.notifier — format logic and notify_user flow."""

import uuid
from datetime import date
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from bot.notifier import ChannelRoute, _format_reminder, notify_user


def _make_route(name: str = "telegram", recipient: str = "111222333") -> ChannelRoute:
    return ChannelRoute(name=name, channel=AsyncMock(), recipient=recipient)


@pytest.mark.unit
class TestFormatReminder:
    def test_overdue_message_contains_warning_and_paid_command(self):
        text = _format_reminder("Netflix", 9.99, "USD", date(2026, 3, 30), 0)

        assert "⚠️" in text
        assert "Netflix" in text
        assert "was due" in text
        assert "/paid" in text

    def test_overdue_message_for_negative_days(self):
        text = _format_reminder("Netflix", 9.99, "USD", date(2026, 3, 29), -1)

        assert "⚠️" in text
        assert "was due" in text

    def test_tomorrow_message_contains_bell_and_tomorrow(self):
        text = _format_reminder("Netflix", 9.99, "USD", date(2026, 4, 1), 1)

        assert "🔔" in text
        assert "tomorrow" in text
        assert "Netflix" in text

    def test_future_message_contains_calendar_and_day_count(self):
        text = _format_reminder("Netflix", 9.99, "USD", date(2026, 4, 7), 7)

        assert "📅" in text
        assert "7 days" in text
        assert "Netflix" in text

    @pytest.mark.parametrize("days_left", [-1, 0, 1, 7])
    def test_amount_included_for_all_reminder_types(self, days_left):
        text = _format_reminder("Bill", 50.00, "EUR", date(2026, 4, 15), days_left)

        assert "50.00 EUR" in text


@pytest.fixture
def mock_user(user_id):
    user = MagicMock()
    user.id = user_id
    user.telegram_id = 111_222_333
    return user


@pytest.mark.unit
class TestNotifyUser:
    async def test_no_due_bills_sends_nothing(self, mock_user, monkeypatch):
        monkeypatch.setattr("bot.notifier.get_due_bills", AsyncMock(return_value=[]))
        session = AsyncMock()
        route = _make_route()

        await notify_user(session, mock_user, [route])

        route.channel.send_message.assert_not_called()

    async def test_already_sent_skips_message_and_log(self, bill, mock_user, monkeypatch):
        due_date = date(2026, 4, 15)
        monkeypatch.setattr(
            "bot.notifier.get_due_bills", AsyncMock(return_value=[(bill, due_date, 3)])
        )
        monkeypatch.setattr("bot.notifier.reminder_already_sent", AsyncMock(return_value=True))
        mock_log = AsyncMock()
        monkeypatch.setattr("bot.notifier.log_reminder", mock_log)
        session = AsyncMock()
        route = _make_route()

        await notify_user(session, mock_user, [route])

        route.channel.send_message.assert_not_called()
        mock_log.assert_not_called()

    async def test_sends_message_and_logs_when_not_sent(self, bill, mock_user, monkeypatch):
        due_date = date(2026, 4, 15)
        monkeypatch.setattr(
            "bot.notifier.get_due_bills", AsyncMock(return_value=[(bill, due_date, 3)])
        )
        monkeypatch.setattr("bot.notifier.reminder_already_sent", AsyncMock(return_value=False))
        mock_log = AsyncMock()
        monkeypatch.setattr("bot.notifier.log_reminder", mock_log)
        session = AsyncMock()
        route = _make_route(recipient=str(mock_user.telegram_id))

        await notify_user(session, mock_user, [route])

        route.channel.send_message.assert_awaited_once_with(str(mock_user.telegram_id), ANY)
        mock_log.assert_awaited_once()

    async def test_sends_message_to_correct_telegram_id(self, bill, mock_user, monkeypatch):
        due_date = date(2026, 4, 15)
        monkeypatch.setattr(
            "bot.notifier.get_due_bills", AsyncMock(return_value=[(bill, due_date, 1)])
        )
        monkeypatch.setattr("bot.notifier.reminder_already_sent", AsyncMock(return_value=False))
        monkeypatch.setattr("bot.notifier.log_reminder", AsyncMock())
        session = AsyncMock()
        route = _make_route(recipient=str(mock_user.telegram_id))

        await notify_user(session, mock_user, [route])

        call_args = route.channel.send_message.call_args
        assert call_args[0][0] == str(mock_user.telegram_id)

    async def test_processes_remaining_bills_when_one_already_sent(self, user_id, monkeypatch):
        bill_a = MagicMock()
        bill_a.id = uuid.uuid4()
        bill_a.name = "A"
        bill_a.amount = 10.0
        bill_a.currency = "USD"

        bill_b = MagicMock()
        bill_b.id = uuid.uuid4()
        bill_b.name = "B"
        bill_b.amount = 20.0
        bill_b.currency = "USD"

        due_date = date(2026, 4, 15)
        monkeypatch.setattr(
            "bot.notifier.get_due_bills",
            AsyncMock(return_value=[(bill_a, due_date, 3), (bill_b, due_date, 3)]),
        )
        monkeypatch.setattr(
            "bot.notifier.reminder_already_sent",
            AsyncMock(side_effect=[True, False]),
        )
        monkeypatch.setattr("bot.notifier.log_reminder", AsyncMock())
        session = AsyncMock()
        user = MagicMock()
        user.id = user_id
        user.telegram_id = 111_222_333
        route = _make_route(recipient=str(user.telegram_id))

        await notify_user(session, user, [route])

        assert route.channel.send_message.await_count == 1

    async def test_sends_via_all_routes(self, bill, mock_user, monkeypatch):
        due_date = date(2026, 4, 15)
        monkeypatch.setattr(
            "bot.notifier.get_due_bills", AsyncMock(return_value=[(bill, due_date, 3)])
        )
        monkeypatch.setattr("bot.notifier.reminder_already_sent", AsyncMock(return_value=False))
        monkeypatch.setattr("bot.notifier.log_reminder", AsyncMock())
        session = AsyncMock()

        route_tg = _make_route("telegram", str(mock_user.telegram_id))
        route_email = _make_route("email", "alice@example.com")

        await notify_user(session, mock_user, [route_tg, route_email])

        route_tg.channel.send_message.assert_awaited_once()
        route_email.channel.send_message.assert_awaited_once_with("alice@example.com", ANY)

    async def test_channel_send_failure_does_not_log_reminder(self, bill, mock_user, monkeypatch):
        due_date = date(2026, 4, 15)
        monkeypatch.setattr(
            "bot.notifier.get_due_bills", AsyncMock(return_value=[(bill, due_date, 3)])
        )
        monkeypatch.setattr("bot.notifier.reminder_already_sent", AsyncMock(return_value=False))
        mock_log = AsyncMock()
        monkeypatch.setattr("bot.notifier.log_reminder", mock_log)
        session = AsyncMock()

        failing_channel = AsyncMock()
        failing_channel.send_message.side_effect = Exception("Resend API error")
        route = ChannelRoute(name="email", channel=failing_channel, recipient="alice@example.com")

        await notify_user(session, mock_user, [route])

        mock_log.assert_not_called()

    async def test_already_sent_on_one_route_does_not_block_other(
        self, bill, mock_user, monkeypatch
    ):
        due_date = date(2026, 4, 15)
        monkeypatch.setattr(
            "bot.notifier.get_due_bills", AsyncMock(return_value=[(bill, due_date, 3)])
        )
        # telegram=True (already sent), email=False (not sent yet)
        monkeypatch.setattr(
            "bot.notifier.reminder_already_sent",
            AsyncMock(side_effect=[True, False]),
        )
        monkeypatch.setattr("bot.notifier.log_reminder", AsyncMock())
        session = AsyncMock()

        route_tg = _make_route("telegram", str(mock_user.telegram_id))
        route_email = _make_route("email", "alice@example.com")

        await notify_user(session, mock_user, [route_tg, route_email])

        route_tg.channel.send_message.assert_not_called()
        route_email.channel.send_message.assert_awaited_once()
