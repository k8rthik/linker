"""Tests for the favorite/cache marker formatter used in the link list."""

from __future__ import annotations

import pytest

from models.link import (
    CACHE_STATUS_CACHED,
    CACHE_STATUS_DOWNLOADING,
    CACHE_STATUS_FAILED,
    CACHE_STATUS_NONE,
    CACHE_STATUS_PENDING,
    Link,
)
from ui.components.link_marker import format_link_marker


def _link(favorite: bool = False, cache_status: str = CACHE_STATUS_NONE) -> Link:
    return Link(
        name="Example",
        url="https://example.com",
        favorite=favorite,
        cache_status=cache_status,
    )


@pytest.mark.unit
def test_marker_empty_for_plain_link():
    assert format_link_marker(_link()) == ""


@pytest.mark.unit
def test_marker_star_for_favorite_only():
    assert format_link_marker(_link(favorite=True)) == "★"


@pytest.mark.unit
def test_marker_cached_glyph_for_cached_non_favorite():
    assert format_link_marker(_link(cache_status=CACHE_STATUS_CACHED)) == "⬇"


@pytest.mark.unit
def test_marker_combines_favorite_and_cached():
    assert (
        format_link_marker(_link(favorite=True, cache_status=CACHE_STATUS_CACHED))
        == "★⬇"
    )


@pytest.mark.unit
def test_marker_pending_shows_ellipsis():
    assert format_link_marker(_link(cache_status=CACHE_STATUS_PENDING)) == "…"


@pytest.mark.unit
def test_marker_downloading_shows_ellipsis():
    assert format_link_marker(_link(cache_status=CACHE_STATUS_DOWNLOADING)) == "…"


@pytest.mark.unit
def test_marker_failed_shows_warning():
    assert format_link_marker(_link(cache_status=CACHE_STATUS_FAILED)) == "⚠"


@pytest.mark.unit
def test_marker_favorite_failed_combined():
    assert (
        format_link_marker(_link(favorite=True, cache_status=CACHE_STATUS_FAILED))
        == "★⚠"
    )
