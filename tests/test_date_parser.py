"""Tests for utils.date_parser."""

from datetime import datetime

import pytest

from utils.date_parser import safe_parse_iso


def test_parses_valid_iso_string():
    result = safe_parse_iso("2026-05-07T12:34:56")
    assert result == datetime(2026, 5, 7, 12, 34, 56)


def test_parses_iso_with_microseconds():
    result = safe_parse_iso("2026-05-07T12:34:56.789012")
    assert result == datetime(2026, 5, 7, 12, 34, 56, 789012)


@pytest.mark.parametrize("value", [None, "", "garbage", "2026/05/07", "not-a-date"])
def test_returns_none_for_invalid_input(value):
    assert safe_parse_iso(value) is None


@pytest.mark.parametrize("value", [123, 1.5, [], {}])
def test_returns_none_for_non_string_input(value):
    assert safe_parse_iso(value) is None


def test_round_trip_with_datetime_isoformat():
    original = datetime(2026, 1, 15, 9, 30)
    parsed = safe_parse_iso(original.isoformat())
    assert parsed == original
