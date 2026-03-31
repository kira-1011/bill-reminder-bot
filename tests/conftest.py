"""Shared pytest fixtures."""

import uuid
from datetime import date

import pytest

from bot.db.models import Bill, Payment, User


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def bill_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def user(user_id: uuid.UUID) -> User:
    return User(id=user_id, telegram_id=111_222_333, username="alice")


@pytest.fixture
def bill(user_id: uuid.UUID, bill_id: uuid.UUID) -> Bill:
    return Bill(
        id=bill_id,
        user_id=user_id,
        name="Netflix",
        amount=9.99,
        currency="USD",
        due_day=15,
        reminder_days=[7, 3, 1],
        enabled=True,
    )


@pytest.fixture
def payment(bill: Bill) -> Payment:
    return Payment(
        id=uuid.uuid4(),
        bill_id=bill.id,
        user_id=bill.user_id,
        cycle_key="2026-04",
        due_date=date(2026, 4, 15),
        status="pending",
    )
