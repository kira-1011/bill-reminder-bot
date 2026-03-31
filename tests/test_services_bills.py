"""Unit tests for bot.services.bills — mocked AsyncSession, no DB required."""

import uuid

import pytest

from bot.services.bills import (
    add_bill,
    delete_bill,
    get_bill,
    get_user_by_telegram_id,
    list_bills,
    upsert_user,
)

from .helpers import make_session


@pytest.mark.unit
class TestUpsertUser:
    async def test_creates_new_user_when_not_found(self):
        session = make_session(scalar=None)

        user = await upsert_user(session, telegram_id=123, username="alice")

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert user.telegram_id == 123
        assert user.username == "alice"

    async def test_updates_username_when_user_exists(self, user):
        session = make_session(scalar=user)

        returned = await upsert_user(session, telegram_id=user.telegram_id, username="bob")

        session.add.assert_not_called()
        assert returned.username == "bob"

    async def test_returns_existing_user_object(self, user):
        session = make_session(scalar=user)

        returned = await upsert_user(session, telegram_id=user.telegram_id, username="alice")

        assert returned is user


@pytest.mark.unit
class TestGetUserByTelegramId:
    async def test_returns_none_when_not_found(self):
        session = make_session(scalar=None)

        result = await get_user_by_telegram_id(session, telegram_id=999)

        assert result is None

    async def test_returns_user_when_found(self, user):
        session = make_session(scalar=user)

        result = await get_user_by_telegram_id(session, telegram_id=user.telegram_id)

        assert result is user


@pytest.mark.unit
class TestAddBill:
    async def test_creates_bill_with_correct_fields(self, user_id):
        session = make_session()

        bill = await add_bill(session, user_id, "Rent", 500.0, "USD", 1)

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert bill.name == "Rent"
        assert bill.amount == 500.0
        assert bill.currency == "USD"
        assert bill.due_day == 1
        assert bill.user_id == user_id


@pytest.mark.unit
class TestListBills:
    async def test_returns_empty_list_when_no_bills(self, user_id):
        session = make_session(scalars=[])

        result = await list_bills(session, user_id)

        assert result == []

    async def test_returns_bills(self, user_id, bill):
        session = make_session(scalars=[bill])

        result = await list_bills(session, user_id)

        assert result == [bill]

    async def test_queries_with_user_id(self, user_id):
        session = make_session(scalars=[])

        await list_bills(session, user_id)

        session.execute.assert_awaited_once()


@pytest.mark.unit
class TestGetBill:
    async def test_returns_none_when_not_found(self, user_id):
        session = make_session(scalar=None)

        result = await get_bill(session, user_id, uuid.uuid4())

        assert result is None

    async def test_returns_bill_when_found(self, user_id, bill):
        session = make_session(scalar=bill)

        result = await get_bill(session, user_id, bill.id)

        assert result is bill


@pytest.mark.unit
class TestDeleteBill:
    async def test_returns_false_when_bill_not_found(self, user_id):
        session = make_session(scalar=None)

        result = await delete_bill(session, user_id, uuid.uuid4())

        assert result is False
        session.delete.assert_not_called()

    async def test_returns_true_when_bill_deleted(self, user_id, bill):
        session = make_session(scalar=bill)

        result = await delete_bill(session, user_id, bill.id)

        assert result is True
        session.delete.assert_awaited_once_with(bill)
