"""Tests for offline-first open routing.

Verifies that ProfileService.open_links uses the cached local file when one
exists, and falls back to the URL otherwise. This is the single decision
point for online-vs-offline open behavior.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from models.link import CACHE_STATUS_NONE, Link
from models.profile import Profile
from repositories.profile_repository import JsonProfileRepository
from services.profile_service import ProfileService


class _StubBrowser:
    def __init__(self):
        self.opened_urls: list[str] = []

    def open_url(self, url: str) -> bool:
        self.opened_urls.append(url)
        return True


class _StubCacheService:
    def __init__(self):
        self._paths: dict[str, Path] = {}
        self.cleared: list[Link] = []

    def set_cached(self, link: Link, path: Path) -> None:
        self._paths[link.url] = path

    def get_cached_path(self, link: Link):
        path = self._paths.get(link.url)
        if path is None:
            return None
        if not path.exists():
            link.clear_cache()
            self.cleared.append(link)
            return None
        return path


@pytest.fixture
def repo_with_links(tmp_path: Path):
    file_path = str(tmp_path / "profiles.json")
    with patch(
        "repositories.profile_repository.get_data_file_path", return_value=file_path
    ):
        repo = JsonProfileRepository(file_path=file_path)
    profile = Profile(
        name="Default",
        is_default=True,
        links=[
            Link(name="Cached", url="https://example.com/cached"),
            Link(name="Uncached", url="https://example.com/uncached"),
        ],
    )
    with patch(
        "repositories.profile_repository.get_data_file_path", return_value=file_path
    ):
        repo.save_all([profile])
        repo.flush_pending_writes()
    return repo


class TestOfflineFirstOpenRouting:
    @pytest.mark.unit
    def test_cached_link_opens_local_file_not_url(
        self, repo_with_links, tmp_path: Path
    ):
        browser = _StubBrowser()
        cache = _StubCacheService()
        cached_file = tmp_path / "video.mp4"
        cached_file.write_bytes(b"x")

        profile = repo_with_links.find_by_name("Default")
        cached_link = profile.links[0]
        cache.set_cached(cached_link, cached_file)

        service = ProfileService(repo_with_links, browser, cache_service=cache)

        with patch("services.link_opener.open_local_file", return_value=True) as opener:
            service.open_links([0])

        opener.assert_called_once_with(cached_file)
        assert browser.opened_urls == []

    @pytest.mark.unit
    def test_uncached_link_opens_url(self, repo_with_links):
        browser = _StubBrowser()
        cache = _StubCacheService()  # nothing cached

        service = ProfileService(repo_with_links, browser, cache_service=cache)

        with patch("services.link_opener.open_local_file", return_value=True) as opener:
            service.open_links([1])

        opener.assert_not_called()
        assert browser.opened_urls == ["https://example.com/uncached"]

    @pytest.mark.unit
    def test_cached_file_missing_falls_back_to_url(
        self, repo_with_links, tmp_path: Path
    ):
        """If the link claims to be cached but the file is gone, route to URL."""
        browser = _StubBrowser()
        cache = _StubCacheService()
        ghost_path = tmp_path / "missing.mp4"  # never created
        profile = repo_with_links.find_by_name("Default")
        cached_link = profile.links[0]
        cache.set_cached(cached_link, ghost_path)

        service = ProfileService(repo_with_links, browser, cache_service=cache)

        with patch("services.link_opener.open_local_file", return_value=True) as opener:
            service.open_links([0])

        opener.assert_not_called()
        assert browser.opened_urls == ["https://example.com/cached"]
        assert cache.cleared == [cached_link]

    @pytest.mark.unit
    def test_no_cache_service_opens_url(self, repo_with_links):
        """ProfileService without a cache_service still opens links via URL."""
        browser = _StubBrowser()
        service = ProfileService(repo_with_links, browser)  # no cache service

        service.open_links([0])

        assert browser.opened_urls == ["https://example.com/cached"]

    @pytest.mark.unit
    def test_cached_link_is_marked_as_opened(self, repo_with_links, tmp_path: Path):
        """Open-count and last_opened still advance when opening offline."""
        browser = _StubBrowser()
        cache = _StubCacheService()
        cached_file = tmp_path / "video.mp4"
        cached_file.write_bytes(b"x")
        profile = repo_with_links.find_by_name("Default")
        link = profile.links[0]
        cache.set_cached(link, cached_file)

        service = ProfileService(repo_with_links, browser, cache_service=cache)

        with patch("services.link_opener.open_local_file", return_value=True):
            service.open_links([0])

        assert link.open_count == 1
        assert link.last_opened is not None

    @pytest.mark.unit
    def test_local_file_open_failure_falls_back_to_url(
        self, repo_with_links, tmp_path: Path
    ):
        """If the OS reports the file open failed, fall back to the URL."""
        browser = _StubBrowser()
        cache = _StubCacheService()
        cached_file = tmp_path / "video.mp4"
        cached_file.write_bytes(b"x")
        profile = repo_with_links.find_by_name("Default")
        link = profile.links[0]
        cache.set_cached(link, cached_file)

        service = ProfileService(repo_with_links, browser, cache_service=cache)

        with patch("services.link_opener.open_local_file", return_value=False):
            service.open_links([0])

        assert browser.opened_urls == ["https://example.com/cached"]

    @pytest.mark.unit
    def test_force_browser_opens_url_even_when_cached(
        self, repo_with_links, tmp_path: Path
    ):
        """force_browser=True bypasses the cache and opens the URL directly."""
        browser = _StubBrowser()
        cache = _StubCacheService()
        cached_file = tmp_path / "video.mp4"
        cached_file.write_bytes(b"x")
        profile = repo_with_links.find_by_name("Default")
        cached_link = profile.links[0]
        cache.set_cached(cached_link, cached_file)

        service = ProfileService(repo_with_links, browser, cache_service=cache)

        with patch("services.link_opener.open_local_file", return_value=True) as opener:
            service.open_links([0], force_browser=True)

        opener.assert_not_called()
        assert browser.opened_urls == ["https://example.com/cached"]

    @pytest.mark.unit
    def test_force_browser_still_marks_as_opened(
        self, repo_with_links, tmp_path: Path
    ):
        """Opening in the browser still advances open-count and last_opened."""
        browser = _StubBrowser()
        cache = _StubCacheService()
        cached_file = tmp_path / "video.mp4"
        cached_file.write_bytes(b"x")
        profile = repo_with_links.find_by_name("Default")
        link = profile.links[0]
        cache.set_cached(link, cached_file)

        service = ProfileService(repo_with_links, browser, cache_service=cache)

        with patch("services.link_opener.open_local_file", return_value=True):
            service.open_links([0], force_browser=True)

        assert link.open_count == 1
        assert link.last_opened is not None


class TestLinkOpenerHelper:
    @pytest.mark.unit
    def test_open_local_file_routes_video_to_quicktime_with_looping(self, tmp_path: Path):
        from services.link_opener import open_local_file

        f = tmp_path / "v.mp4"
        f.write_bytes(b"x")

        with patch("sys.platform", "darwin"), patch(
            "subprocess.run", return_value=MagicMock(returncode=0)
        ) as run:
            assert open_local_file(f) is True
        run.assert_called_once()
        cmd = run.call_args.args[0]
        assert cmd[0] == "osascript"
        # The AppleScript body is passed via -e and must enable looping.
        assert "-e" in cmd
        script = cmd[cmd.index("-e") + 1]
        assert "QuickTime Player" in script
        assert "set looping of theDoc to true" in script
        assert cmd[-1] == str(f)

    @pytest.mark.unit
    def test_open_local_file_non_video_uses_macos_open(self, tmp_path: Path):
        from services.link_opener import open_local_file

        f = tmp_path / "notes.txt"
        f.write_bytes(b"x")

        with patch("sys.platform", "darwin"), patch(
            "subprocess.run", return_value=MagicMock(returncode=0)
        ) as run:
            assert open_local_file(f) is True
        run.assert_called_once()
        cmd = run.call_args.args[0]
        assert cmd[0] == "open"
        assert cmd[1] == str(f)

    @pytest.mark.unit
    def test_open_local_file_returns_false_on_missing_file(self, tmp_path: Path):
        from services.link_opener import open_local_file

        ghost = tmp_path / "ghost.mp4"
        assert open_local_file(ghost) is False

    @pytest.mark.unit
    def test_open_local_file_returns_false_on_subprocess_error(self, tmp_path: Path):
        from services.link_opener import open_local_file
        import subprocess

        f = tmp_path / "v.mp4"
        f.write_bytes(b"x")

        with patch("sys.platform", "darwin"), patch(
            "subprocess.run", side_effect=subprocess.SubprocessError("boom")
        ):
            assert open_local_file(f) is False
