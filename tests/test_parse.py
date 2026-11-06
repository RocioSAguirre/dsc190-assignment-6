from datetime import date

import pytest

from nldate import parse

TODAY = date(2026, 11, 5)  # a Thursday


def test_no_today_given():
    assert parse("today") == date.today()


def test_tomorrow():
    assert parse("tomorrow", today=TODAY) == date(2026, 11, 6)


def test_relative():
    assert parse("in 8 days from now", today=TODAY) == date(2026, 11, 13)


def test_weeks():
    assert parse("2 weeks from tomorrow", today=TODAY) == date(2026, 11, 20)


def test_relative_weekdays():
    assert parse("4 Monday's from now", today=TODAY) == date(2026, 11, 30)


def test_days_before_absolute_date():
    assert parse("5 days before December 1st, 2025", today=TODAY) == date(2025, 11, 26)


def test_days_after_absolute_date():
    assert parse("5 days after December 1st, 2025", today=TODAY) == date(2025, 12, 6)


def test_combined_dates():
    assert parse(
        "a year, 2 weeks, and 1 day from November 30th, 2025", today=TODAY
    ) == date(2026, 12, 15)


def test_empty_string_raises():
    with pytest.raises(ValueError):
        parse("", today=TODAY)


def test_invalid_string_raises():
    with pytest.raises(ValueError):
        parse("lalala", today=TODAY)
