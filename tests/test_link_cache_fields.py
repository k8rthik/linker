"""Tests for Link model cache-related fields (Phase 1 of offline cache feature)."""

from __future__ import annotations

import pytest

from models.link import (
    CACHE_STATUS_CACHED,
    CACHE_STATUS_DOWNLOADING,
    CACHE_STATUS_FAILED,
    CACHE_STATUS_NONE,
    CACHE_STATUS_PENDING,
    VALID_CACHE_STATUSES,
    Link,
)


class TestLinkCacheFieldDefaults:
    @pytest.mark.unit
    def test_new_link_has_cache_status_none_by_default(self) -> None:
        link = Link(name="Example", url="https://example.com")
        assert link.cache_status == CACHE_STATUS_NONE

    @pytest.mark.unit
    def test_new_link_has_no_cached_path_by_default(self) -> None:
        link = Link(name="Example", url="https://example.com")
        assert link.cached_path is None

    @pytest.mark.unit
    def test_new_link_has_no_cache_size_by_default(self) -> None:
        link = Link(name="Example", url="https://example.com")
        assert link.cache_size_bytes is None

    @pytest.mark.unit
    def test_new_link_has_no_cache_error_by_default(self) -> None:
        link = Link(name="Example", url="https://example.com")
        assert link.cache_error is None


class TestLinkCacheFieldValidation:
    @pytest.mark.unit
    def test_invalid_cache_status_raises(self) -> None:
        with pytest.raises(ValueError):
            Link(name="Example", url="https://example.com", cache_status="garbage")

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "status",
        [
            CACHE_STATUS_NONE,
            CACHE_STATUS_PENDING,
            CACHE_STATUS_DOWNLOADING,
            CACHE_STATUS_CACHED,
            CACHE_STATUS_FAILED,
        ],
    )
    def test_all_valid_statuses_accepted(self, status: str) -> None:
        link = Link(name="Example", url="https://example.com", cache_status=status)
        assert link.cache_status == status

    @pytest.mark.unit
    def test_valid_status_set_is_complete(self) -> None:
        assert VALID_CACHE_STATUSES == {
            CACHE_STATUS_NONE,
            CACHE_STATUS_PENDING,
            CACHE_STATUS_DOWNLOADING,
            CACHE_STATUS_CACHED,
            CACHE_STATUS_FAILED,
        }

    @pytest.mark.unit
    def test_negative_cache_size_clamped_to_zero(self) -> None:
        link = Link(
            name="Example",
            url="https://example.com",
            cache_size_bytes=-100,
        )
        assert link.cache_size_bytes == 0


class TestLinkCacheStateHelpers:
    @pytest.mark.unit
    def test_is_cached_true_only_when_status_cached_and_path_present(self) -> None:
        link = Link(
            name="Example",
            url="https://example.com",
            cache_status=CACHE_STATUS_CACHED,
            cached_path="/tmp/foo.mp4",
        )
        assert link.is_cached() is True

    @pytest.mark.unit
    def test_is_cached_false_when_status_cached_but_no_path(self) -> None:
        link = Link(
            name="Example",
            url="https://example.com",
            cache_status=CACHE_STATUS_CACHED,
        )
        assert link.is_cached() is False

    @pytest.mark.unit
    def test_is_cached_false_for_other_statuses(self) -> None:
        for status in (
            CACHE_STATUS_NONE,
            CACHE_STATUS_PENDING,
            CACHE_STATUS_DOWNLOADING,
            CACHE_STATUS_FAILED,
        ):
            link = Link(
                name="Example",
                url="https://example.com",
                cache_status=status,
                cached_path="/tmp/foo.mp4",
            )
            assert link.is_cached() is False


class TestLinkCacheSerialization:
    @pytest.mark.unit
    def test_to_dict_includes_cache_fields(self) -> None:
        link = Link(
            name="Example",
            url="https://example.com",
            cache_status=CACHE_STATUS_CACHED,
            cached_path="/tmp/foo.mp4",
            cache_size_bytes=1024,
            cache_error=None,
        )
        data = link.to_dict()
        assert data["cache_status"] == CACHE_STATUS_CACHED
        assert data["cached_path"] == "/tmp/foo.mp4"
        assert data["cache_size_bytes"] == 1024
        assert data["cache_error"] is None

    @pytest.mark.unit
    def test_from_dict_restores_cache_fields(self) -> None:
        data = {
            "name": "Example",
            "url": "https://example.com",
            "cache_status": CACHE_STATUS_FAILED,
            "cached_path": None,
            "cache_size_bytes": None,
            "cache_error": "yt-dlp: HTTP 403",
        }
        link = Link.from_dict(data)
        assert link.cache_status == CACHE_STATUS_FAILED
        assert link.cached_path is None
        assert link.cache_size_bytes is None
        assert link.cache_error == "yt-dlp: HTTP 403"

    @pytest.mark.unit
    def test_from_dict_missing_cache_fields_defaults_to_none_status(self) -> None:
        """Backward compatibility: legacy data without cache fields loads cleanly."""
        data = {"name": "Example", "url": "https://example.com"}
        link = Link.from_dict(data)
        assert link.cache_status == CACHE_STATUS_NONE
        assert link.cached_path is None
        assert link.cache_size_bytes is None
        assert link.cache_error is None

    @pytest.mark.unit
    def test_roundtrip_preserves_cache_fields(self) -> None:
        original = Link(
            name="Example",
            url="https://example.com",
            cache_status=CACHE_STATUS_DOWNLOADING,
            cached_path="/tmp/in-progress.part",
            cache_size_bytes=512,
            cache_error=None,
        )
        restored = Link.from_dict(original.to_dict())
        assert restored.cache_status == original.cache_status
        assert restored.cached_path == original.cached_path
        assert restored.cache_size_bytes == original.cache_size_bytes
        assert restored.cache_error == original.cache_error


class TestLinkCacheTransitions:
    @pytest.mark.unit
    def test_mark_cache_pending_clears_error(self) -> None:
        link = Link(
            name="Example",
            url="https://example.com",
            cache_status=CACHE_STATUS_FAILED,
            cache_error="previous failure",
        )
        link.mark_cache_pending()
        assert link.cache_status == CACHE_STATUS_PENDING
        assert link.cache_error is None

    @pytest.mark.unit
    def test_mark_cache_downloading_sets_status(self) -> None:
        link = Link(name="Example", url="https://example.com")
        link.mark_cache_downloading()
        assert link.cache_status == CACHE_STATUS_DOWNLOADING

    @pytest.mark.unit
    def test_mark_cached_sets_path_size_and_clears_error(self) -> None:
        link = Link(
            name="Example",
            url="https://example.com",
            cache_status=CACHE_STATUS_DOWNLOADING,
            cache_error="stale",
        )
        link.mark_cached(path="/tmp/foo.mp4", size_bytes=2048)
        assert link.cache_status == CACHE_STATUS_CACHED
        assert link.cached_path == "/tmp/foo.mp4"
        assert link.cache_size_bytes == 2048
        assert link.cache_error is None

    @pytest.mark.unit
    def test_mark_cache_failed_records_error_and_clears_path(self) -> None:
        link = Link(
            name="Example",
            url="https://example.com",
            cache_status=CACHE_STATUS_DOWNLOADING,
            cached_path="/tmp/partial.part",
            cache_size_bytes=100,
        )
        link.mark_cache_failed("network error")
        assert link.cache_status == CACHE_STATUS_FAILED
        assert link.cache_error == "network error"
        assert link.cached_path is None
        assert link.cache_size_bytes is None

    @pytest.mark.unit
    def test_clear_cache_resets_to_none(self) -> None:
        link = Link(
            name="Example",
            url="https://example.com",
            cache_status=CACHE_STATUS_CACHED,
            cached_path="/tmp/foo.mp4",
            cache_size_bytes=1024,
        )
        link.clear_cache()
        assert link.cache_status == CACHE_STATUS_NONE
        assert link.cached_path is None
        assert link.cache_size_bytes is None
        assert link.cache_error is None
