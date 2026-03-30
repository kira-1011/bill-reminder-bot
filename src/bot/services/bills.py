import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Bill, User

logger = logging.getLogger(__name__)


async def upsert_user(session: AsyncSession, telegram_id: int, username: str | None) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.flush()
        logger.info("New user created telegram_id=%s", telegram_id)
    else:
        user.username = username
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def add_bill(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    amount: float,
    currency: str,
    due_day: int,
) -> Bill:
    bill = Bill(
        user_id=user_id,
        name=name,
        amount=amount,
        currency=currency,
        due_day=due_day,
    )
    session.add(bill)
    await session.flush()
    logger.info(
        "Bill created bill_id=%s user_id=%s name=%r due_day=%s", bill.id, user_id, name, due_day
    )
    return bill


async def list_bills(session: AsyncSession, user_id: uuid.UUID) -> list[Bill]:
    result = await session.execute(
        select(Bill).where(Bill.user_id == user_id, Bill.enabled == True).order_by(Bill.due_day)  # noqa: E712
    )
    return list(result.scalars().all())


async def get_bill(session: AsyncSession, user_id: uuid.UUID, bill_id: uuid.UUID) -> Bill | None:
    result = await session.execute(select(Bill).where(Bill.id == bill_id, Bill.user_id == user_id))
    return result.scalar_one_or_none()


async def delete_bill(session: AsyncSession, user_id: uuid.UUID, bill_id: uuid.UUID) -> bool:
    bill = await get_bill(session, user_id, bill_id)
    if bill is None:
        logger.warning("Delete attempted on unknown bill bill_id=%s user_id=%s", bill_id, user_id)
        return False
    await session.delete(bill)
    logger.info("Bill deleted bill_id=%s user_id=%s name=%r", bill_id, user_id, bill.name)
    return True
