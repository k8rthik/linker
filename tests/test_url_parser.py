"""Tests for utils.url_parser."""

import pytest

from utils.url_parser import extract_domain


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://example.com/path", "example.com"),
        ("http://example.com", "example.com"),
        ("https://www.example.com/foo?bar=1", "www.example.com"),
        ("example.com", "example.com"),
        ("example.com/path", "example.com"),
        ("https://sub.domain.example.com:8080/x", "sub.domain.example.com:8080"),
        ("https://EXAMPLE.com/X", "EXAMPLE.com"),
    ],
)
def test_extracts_expected_domain(url, expected):
    assert extract_domain(url) == expected


@pytest.mark.parametrize("url", ["", None])
def test_returns_empty_string_for_empty_input(url):
    assert extract_domain(url) == ""


def test_handles_url_without_path():
    assert extract_domain("https://example.com") == "example.com"


def test_matches_legacy_link_extract_domain_behavior():
    """Sanity: the new helper preserves Link._extract_domain's existing semantics."""
    from models.link import Link

    samples = [
        "https://example.com",
        "http://www.test.org/path",
        "fyptt.to/abc123",
        "",
    ]
    for url in samples:
        assert extract_domain(url) == Link._extract_domain(url)
