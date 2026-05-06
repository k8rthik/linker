"""Tests for human-readable byte size formatting."""

import pytest

from utils.size_formatter import format_size_bytes


@pytest.mark.parametrize(
    "n,expected",
    [
        (0, "0 B"),
        (512, "512 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1024 * 1024, "1.0 MB"),
        (int(1.5 * 1024 * 1024), "1.5 MB"),
        (1024 * 1024 * 1024, "1.0 GB"),
        (5 * 1024 * 1024 * 1024, "5.0 GB"),
        (1024 ** 4, "1.0 TB"),
    ],
)
def test_format_size_bytes(n: int, expected: str) -> None:
    assert format_size_bytes(n) == expected


def test_negative_treated_as_zero() -> None:
    assert format_size_bytes(-100) == "0 B"
