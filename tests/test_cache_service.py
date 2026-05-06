"""Tests for CacheService — queue, state machine, persistence integration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from unittest.mock import patch

import pytest

from models.link import (
    CACHE_STATUS_CACHED,
    CACHE_STATUS_FAILED,
    CACHE_STATUS_NONE,
    CACHE_STATUS_PENDING,
    Link,
)
from models.profile import Profile
from repositories.profile_repository import JsonProfileRepository
from services.cache_service import CacheService
from utils.video_downloader import DownloadResult, VideoDownloader


@dataclass
class _RecordedCall:
    url: str
    dest_dir: Path


class _FakeDownloader(VideoDownloader):
    """Test double — produces a file in dest_dir and records calls."""

    def __init__(self) -> None:
        self.calls: List[_RecordedCall] = []
        self._next_result: Optional[DownloadResult] = None
        self._available = True

    def set_available(self, value: bool) -> None:
        self._available = value

    def queue_success(self, content: bytes = b"video-bytes") -> None:
        self._next_content = content
        self._next_result = None  # signal "create file from content"

    def queue_failure(self, error: str) -> None:
        self._next_result = DownloadResult.failure(error)

    def is_available(self) -> bool:
        return self._available

    def download(self, url: str, dest_dir: Path) -> DownloadResult:
        self.calls.append(_RecordedCall(url=url, dest_dir=dest_dir))
        if self._next_result is not None:
            return self._next_result
        # Default: write a file
        path = dest_dir / "fake.mp4"
        path.write_bytes(getattr(self, "_next_content", b"video-bytes"))
        return DownloadResult.success_(file_path=path, size_bytes=path.stat().st_size)


@pytest.fixture
def repo(tmp_path: Path):
    file_path = str(tmp_path / "profiles.json")
    with patch(
        "repositories.profile_repository.get_data_file_path", return_value=file_path
    ):
        repo = JsonProfileRepository(file_path=file_path)
    profile = Profile(
        name="Default",
        is_default=True,
        links=[
            Link(name="A", url="https://example.com/a"),
            Link(name="B", url="https://example.com/b"),
        ],
    )
    with patch(
        "repositories.profile_repository.get_data_file_path", return_value=file_path
    ):
        repo.save_all([profile])
        repo.flush_pending_writes()
    return repo


@pytest.fixture
def fake_downloader() -> _FakeDownloader:
    return _FakeDownloader()


@pytest.fixture
def cache_service(tmp_path: Path, repo, fake_downloader):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    service = CacheService(
        repository=repo,
        downloader=fake_downloader,
        cache_dir=cache_dir,
        synchronous=True,  # process jobs inline for deterministic tests
    )
    yield service
    service.shutdown()


class TestEnqueueAndDownload:
    @pytest.mark.unit
    def test_enqueue_marks_link_cached_on_success(
        self, cache_service: CacheService, repo, fake_downloader
    ) -> None:
        fake_downloader.queue_success(content=b"x" * 100)
        link = repo.find_by_name("Default").links[0]

        cache_service.enqueue("Default", link)

        assert link.cache_status == CACHE_STATUS_CACHED
        assert link.cached_path is not None
        assert Path(link.cached_path).exists()
        assert link.cache_size_bytes == 100
        assert link.cache_error is None

    @pytest.mark.unit
    def test_enqueue_persists_status_on_completion(
        self, cache_service: CacheService, repo, fake_downloader
    ) -> None:
        link = repo.find_by_name("Default").links[0]
        cache_service.enqueue("Default", link)
        repo.flush_pending_writes()

        # Reload from disk and confirm persistence
        from repositories.profile_repository import JsonProfileRepository

        with patch(
            "repositories.profile_repository.get_data_file_path",
            return_value=repo._file_path,
        ):
            fresh = JsonProfileRepository(file_path=repo._file_path)
        reloaded = fresh.find_by_name("Default").links[0]
        assert reloaded.cache_status == CACHE_STATUS_CACHED
        assert reloaded.cached_path is not None

    @pytest.mark.unit
    def test_enqueue_failure_marks_failed_with_error(
        self, cache_service: CacheService, repo, fake_downloader
    ) -> None:
        fake_downloader.queue_failure("yt-dlp: HTTP 403")
        link = repo.find_by_name("Default").links[0]

        cache_service.enqueue("Default", link)

        assert link.cache_status == CACHE_STATUS_FAILED
        assert link.cache_error == "yt-dlp: HTTP 403"
        assert link.cached_path is None

    @pytest.mark.unit
    def test_enqueue_skips_already_cached_link(
        self, cache_service: CacheService, repo, fake_downloader
    ) -> None:
        link = repo.find_by_name("Default").links[0]
        cache_service.enqueue("Default", link)
        assert link.cache_status == CACHE_STATUS_CACHED
        first_call_count = len(fake_downloader.calls)

        cache_service.enqueue("Default", link)
        # Should not have triggered a second download
        assert len(fake_downloader.calls) == first_call_count

    @pytest.mark.unit
    def test_enqueue_when_downloader_unavailable_marks_failed(
        self, cache_service: CacheService, repo, fake_downloader
    ) -> None:
        fake_downloader.set_available(False)
        link = repo.find_by_name("Default").links[0]

        cache_service.enqueue("Default", link)

        assert link.cache_status == CACHE_STATUS_FAILED
        assert "yt-dlp" in (link.cache_error or "").lower()


class TestRetry:
    @pytest.mark.unit
    def test_retry_failed_link_clears_error_and_redownloads(
        self, cache_service: CacheService, repo, fake_downloader
    ) -> None:
        link = repo.find_by_name("Default").links[0]
        fake_downloader.queue_failure("transient")
        cache_service.enqueue("Default", link)
        assert link.cache_status == CACHE_STATUS_FAILED

        # Reset fake to succeed and retry
        fake_downloader.queue_success()
        cache_service.retry("Default", link)

        assert link.cache_status == CACHE_STATUS_CACHED
        assert link.cache_error is None


class TestDeleteCached:
    @pytest.mark.unit
    def test_delete_cached_removes_file_and_resets_state(
        self, cache_service: CacheService, repo, fake_downloader
    ) -> None:
        link = repo.find_by_name("Default").links[0]
        cache_service.enqueue("Default", link)
        cached_file = Path(link.cached_path)
        assert cached_file.exists()

        cache_service.delete_cached("Default", link)

        assert not cached_file.exists()
        assert link.cache_status == CACHE_STATUS_NONE
        assert link.cached_path is None
        assert link.cache_size_bytes is None


class TestClearAll:
    @pytest.mark.unit
    def test_clear_all_removes_files_and_resets_all_links(
        self, cache_service: CacheService, repo, fake_downloader
    ) -> None:
        profile = repo.find_by_name("Default")
        for link in profile.links:
            cache_service.enqueue("Default", link)

        for link in profile.links:
            assert link.cache_status == CACHE_STATUS_CACHED

        cache_service.clear_all()

        for link in profile.links:
            assert link.cache_status == CACHE_STATUS_NONE
            assert link.cached_path is None

        # Cache directory should be empty
        assert not any(cache_service.cache_dir.iterdir())


class TestCacheLookup:
    @pytest.mark.unit
    def test_get_cached_path_returns_path_when_file_exists(
        self, cache_service: CacheService, repo, fake_downloader
    ) -> None:
        link = repo.find_by_name("Default").links[0]
        cache_service.enqueue("Default", link)

        path = cache_service.get_cached_path(link)
        assert path is not None
        assert path.exists()

    @pytest.mark.unit
    def test_get_cached_path_resets_state_if_file_missing(
        self, cache_service: CacheService, repo, fake_downloader
    ) -> None:
        link = repo.find_by_name("Default").links[0]
        cache_service.enqueue("Default", link)
        # User deleted the file behind our back
        os.remove(link.cached_path)

        path = cache_service.get_cached_path(link)

        assert path is None
        assert link.cache_status == CACHE_STATUS_NONE


class TestTotalSize:
    @pytest.mark.unit
    def test_total_size_sums_cached_links(
        self, cache_service: CacheService, repo, fake_downloader
    ) -> None:
        profile = repo.find_by_name("Default")

        fake_downloader.queue_success(content=b"x" * 100)
        cache_service.enqueue("Default", profile.links[0])
        fake_downloader.queue_success(content=b"y" * 250)
        cache_service.enqueue("Default", profile.links[1])

        assert cache_service.total_size_bytes() == 350

    @pytest.mark.unit
    def test_total_size_zero_when_nothing_cached(
        self, cache_service: CacheService
    ) -> None:
        assert cache_service.total_size_bytes() == 0
