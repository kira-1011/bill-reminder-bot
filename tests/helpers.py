"""Shared test helpers — not pytest fixtures (those live in conftest.py)."""

from unittest.mock import AsyncMock, MagicMock


def make_session(*, scalar=None, scalars=None):
    """Return a mock AsyncSession with pre-configured execute results.

    scalar  — value returned by result.scalar_one_or_none()
    scalars — list returned by result.scalars().all()
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    result.scalars.return_value.all.return_value = scalars or []

    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    return session
