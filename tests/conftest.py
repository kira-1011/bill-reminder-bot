"""Shared pytest fixtures."""

import os
import uuid
from datetime import date

# Set required env vars before any bot modules are imported.
# bot.config.Settings() is instantiated at module level, so these must be
# in place before pytest collects (imports) the test files.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("RESEND_API_KEY", "test-key")
os.environ.setdefault("RESEND_FROM_ADDRESS", "test@example.com")

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
