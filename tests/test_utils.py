"""Unit tests for bot.utils — all pure functions, no mocks needed."""

from datetime import date

import pytest

from bot.utils import (
    compute_due_date,
    days_until,
    format_amount,
    format_due_date,
    get_cycle_key,
)


class TestGetCycleKey:
    def test_formats_year_and_zero_padded_month(self):
        assert get_cycle_key(date(2026, 3, 31)) == "2026-03"

    def test_pads_single_digit_month(self):
        assert get_cycle_key(date(2026, 1, 1)) == "2026-01"

    def test_december(self):
        assert get_cycle_key(date(2026, 12, 15)) == "2026-12"


class TestComputeDueDate:
    def test_due_day_equals_today_returns_same_month(self):
        today = date(2026, 3, 15)
        assert compute_due_date(15, today) == date(2026, 3, 15)

    def test_due_day_later_this_month(self):
        today = date(2026, 3, 10)
        assert compute_due_date(20, today) == date(2026, 3, 20)

    def test_due_day_already_passed_returns_next_month(self):
        today = date(2026, 3, 20)
        assert compute_due_date(10, today) == date(2026, 4, 10)

    def test_december_wraps_to_january_next_year(self):
        today = date(2026, 12, 20)
        assert compute_due_date(10, today) == date(2027, 1, 10)

    def test_december_same_month_when_day_not_passed(self):
        today = date(2026, 12, 5)
        assert compute_due_date(10, today) == date(2026, 12, 10)

    @pytest.mark.parametrize("due_day", [1, 14, 28])
    def test_boundary_due_days(self, due_day):
        today = date(2026, 4, 1)
        result = compute_due_date(due_day, today)
        assert result.day == due_day
        assert result >= today


class TestDaysUntil:
    def test_future_date(self):
        assert days_until(date(2026, 4, 10), date(2026, 4, 3)) == 7

    def test_same_day_returns_zero(self):
        assert days_until(date(2026, 4, 10), date(2026, 4, 10)) == 0

    def test_past_date_returns_negative(self):
        assert days_until(date(2026, 4, 3), date(2026, 4, 10)) == -7


class TestFormatAmount:
    def test_formats_with_two_decimal_places(self):
        assert format_amount(9.99, "USD") == "9.99 USD"

    def test_adds_thousands_separator(self):
        assert format_amount(1_500.00, "EUR") == "1,500.00 EUR"

    def test_zero_amount(self):
        assert format_amount(0, "GBP") == "0.00 GBP"

    def test_empty_currency(self):
        assert format_amount(9.99, "") == "9.99 "


class TestFormatDueDate:
    def test_formats_day_month_year(self):
        assert format_due_date(date(2026, 3, 5)) == "05 Mar 2026"

    def test_zero_pads_day(self):
        assert format_due_date(date(2026, 1, 1)) == "01 Jan 2026"

    def test_december(self):
        assert format_due_date(date(2026, 12, 25)) == "25 Dec 2026"
