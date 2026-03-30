import uuid

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    bills: Mapped[list["Bill"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(Text, server_default="USD")
    due_day: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )  # CHECK 1–28 enforced in migration
    recurrence: Mapped[str] = mapped_column(Text, server_default="monthly")
    reminder_days: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, server_default="{7,3,1}"
    )
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="bills")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan"
    )
    reminder_logs: Mapped[list["ReminderLog"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan"
    )


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("bill_id", "cycle_key", name="uq_payment_bill_cycle"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    cycle_key: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. '2026-04'
    due_date: Mapped[str] = mapped_column(Date, nullable=False)
    paid_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(Text, server_default="pending")  # pending | paid | missed
    created_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    bill: Mapped["Bill"] = relationship(back_populates="payments")


class ReminderLog(Base):
    __tablename__ = "reminder_log"
    __table_args__ = (
        UniqueConstraint("bill_id", "due_date", "channel", "offset_days", name="uq_reminder_log"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False
    )
    due_date: Mapped[str] = mapped_column(Date, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    offset_days: Mapped[int] = mapped_column(Integer, nullable=False)
    sent_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    bill: Mapped["Bill"] = relationship(back_populates="reminder_logs")
