"""Unit tests for bot.services.payments — mocked session + patched today_local."""

from datetime import date

import pytest

from bot.services.payments import (
    get_due_bills,
    get_or_create_payment,
    log_reminder,
    mark_paid,
    reminder_already_sent,
)

from .helpers import make_session


@pytest.mark.unit
class TestGetOrCreatePayment:
    async def test_returns_existing_payment(self, bill, payment):
        session = make_session(scalar=payment)

        result = await get_or_create_payment(session, bill, "2026-04", payment.due_date)

        session.add.assert_not_called()
        assert result is payment

    async def test_creates_payment_when_not_found(self, bill):
        session = make_session(scalar=None)
        due_date = date(2026, 4, 15)

        result = await get_or_create_payment(session, bill, "2026-04", due_date)

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert result.cycle_key == "2026-04"
        assert result.status == "pending"
        assert result.bill_id == bill.id


@pytest.mark.unit
class TestMarkPaid:
    async def test_sets_status_to_paid(self, bill, payment, monkeypatch):
        monkeypatch.setattr("bot.services.payments.today_local", lambda: date(2026, 4, 10))
        session = make_session(scalar=payment)

        result = await mark_paid(session, bill, "2026-04", payment.due_date)

        assert result.status == "paid"
        assert result.paid_date == date(2026, 4, 10)

    async def test_sets_custom_amount_when_provided(self, bill, payment, monkeypatch):
        monkeypatch.setattr("bot.services.payments.today_local", lambda: date(2026, 4, 10))
        session = make_session(scalar=payment)

        result = await mark_paid(session, bill, "2026-04", payment.due_date, paid_amount=12.50)

        assert result.amount == 12.50

    async def test_does_not_override_amount_when_not_provided(self, bill, payment, monkeypatch):
        monkeypatch.setattr("bot.services.payments.today_local", lambda: date(2026, 4, 10))
        payment.amount = 9.99
        session = make_session(scalar=payment)

        result = await mark_paid(session, bill, "2026-04", payment.due_date)

        assert result.amount == 9.99


@pytest.mark.unit
class TestReminderAlreadySent:
    async def test_returns_true_when_log_exists(self, bill):
        from bot.db.models import ReminderLog

        log = ReminderLog(
            bill_id=bill.id,
            due_date=date(2026, 4, 15),
            channel="telegram",
            offset_days=3,
        )
        session = make_session(scalar=log)

        result = await reminder_already_sent(session, bill.id, date(2026, 4, 15), "telegram", 3)

        assert result is True

    async def test_returns_false_when_no_log(self, bill):
        session = make_session(scalar=None)

        result = await reminder_already_sent(session, bill.id, date(2026, 4, 15), "telegram", 3)

        assert result is False


@pytest.mark.unit
class TestLogReminder:
    async def test_adds_reminder_log_to_session(self, bill):
        session = make_session()

        await log_reminder(session, bill.id, date(2026, 4, 15), "telegram", 3)

        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert added.bill_id == bill.id
        assert added.due_date == date(2026, 4, 15)
        assert added.channel == "telegram"
        assert added.offset_days == 3


@pytest.mark.unit
class TestGetDueBills:
    async def test_includes_bill_when_days_left_in_reminder_days(self, bill, monkeypatch):
        # today=Apr 8, due_day=15 → due_date=Apr 15, days_left=7 → in [7,3,1]
        monkeypatch.setattr("bot.services.payments.today_local", lambda: date(2026, 4, 8))
        session = make_session(scalars=[bill])

        result = await get_due_bills(session, bill.user_id)

        assert len(result) == 1
        out_bill, due_date, days_left = result[0]
        assert out_bill is bill
        assert days_left == 7
        assert due_date == date(2026, 4, 15)

    async def test_excludes_bill_when_days_left_not_in_reminder_days(self, bill, monkeypatch):
        # today=Apr 10, due_day=15 → due_date=Apr 15, days_left=5 → not in [7,3,1]
        monkeypatch.setattr("bot.services.payments.today_local", lambda: date(2026, 4, 10))
        session = make_session(scalars=[bill])

        result = await get_due_bills(session, bill.user_id)

        assert result == []

    async def test_includes_bill_due_today(self, bill, monkeypatch):
        # today=Apr 15, due_day=15 → due_date=Apr 15, days_left=0 → overdue
        monkeypatch.setattr("bot.services.payments.today_local", lambda: date(2026, 4, 15))
        session = make_session(scalars=[bill])

        result = await get_due_bills(session, bill.user_id)

        assert len(result) == 1
        _, _, days_left = result[0]
        assert days_left == 0

    async def test_returns_empty_when_no_bills(self, user_id, monkeypatch):
        monkeypatch.setattr("bot.services.payments.today_local", lambda: date(2026, 4, 8))
        session = make_session(scalars=[])

        result = await get_due_bills(session, user_id)

        assert result == []
