"""Tests for the video downloader (yt-dlp subprocess wrapper)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from utils.video_downloader import DownloadResult, YtDlpDownloader


class TestYtDlpDownloaderAvailability:
    @pytest.mark.unit
    def test_is_available_true_when_binary_on_path(self, tmp_path: Path) -> None:
        downloader = YtDlpDownloader()
        with patch("shutil.which", return_value="/usr/local/bin/yt-dlp"):
            assert downloader.is_available() is True

    @pytest.mark.unit
    def test_is_available_false_when_binary_missing(self) -> None:
        downloader = YtDlpDownloader()
        with patch("shutil.which", return_value=None):
            assert downloader.is_available() is False


class TestYtDlpDownloaderDownload:
    @pytest.mark.unit
    def test_download_success_returns_path_and_size(self, tmp_path: Path) -> None:
        # Simulate yt-dlp creating a file in tmp_path and printing its path
        produced = tmp_path / "video.mp4"
        produced.write_bytes(b"x" * 1234)

        completed = MagicMock(spec=subprocess.CompletedProcess)
        completed.returncode = 0
        completed.stdout = f"{produced}\n"
        completed.stderr = ""

        downloader = YtDlpDownloader()
        with patch("subprocess.run", return_value=completed):
            result = downloader.download("https://example.com/v/123", tmp_path)

        assert result.success is True
        assert result.file_path == produced
        assert result.size_bytes == 1234
        assert result.error is None

    @pytest.mark.unit
    def test_download_failure_returns_error(self, tmp_path: Path) -> None:
        completed = MagicMock(spec=subprocess.CompletedProcess)
        completed.returncode = 1
        completed.stdout = ""
        completed.stderr = "ERROR: Unsupported URL"

        downloader = YtDlpDownloader()
        with patch("subprocess.run", return_value=completed):
            result = downloader.download("https://bad", tmp_path)

        assert result.success is False
        assert result.file_path is None
        assert result.size_bytes is None
        assert "Unsupported URL" in (result.error or "")

    @pytest.mark.unit
    def test_download_missing_file_after_yt_dlp_success_is_failure(
        self, tmp_path: Path
    ) -> None:
        """yt-dlp returned 0 but the printed path doesn't exist on disk."""
        completed = MagicMock(spec=subprocess.CompletedProcess)
        completed.returncode = 0
        completed.stdout = str(tmp_path / "ghost.mp4") + "\n"
        completed.stderr = ""

        downloader = YtDlpDownloader()
        with patch("subprocess.run", return_value=completed):
            result = downloader.download("https://example.com/v", tmp_path)

        assert result.success is False
        assert result.error is not None

    @pytest.mark.unit
    def test_download_timeout_returns_error(self, tmp_path: Path) -> None:
        downloader = YtDlpDownloader(timeout_seconds=1)
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="yt-dlp", timeout=1),
        ):
            result = downloader.download("https://slow", tmp_path)

        assert result.success is False
        assert "timeout" in (result.error or "").lower()

    @pytest.mark.unit
    def test_download_binary_not_found_returns_error(self, tmp_path: Path) -> None:
        downloader = YtDlpDownloader()
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = downloader.download("https://example.com", tmp_path)

        assert result.success is False
        assert "yt-dlp" in (result.error or "").lower()


class TestDownloadResult:
    @pytest.mark.unit
    def test_success_factory(self, tmp_path: Path) -> None:
        path = tmp_path / "x.mp4"
        path.write_bytes(b"abc")
        result = DownloadResult.success_(file_path=path, size_bytes=3)
        assert result.success is True
        assert result.file_path == path
        assert result.size_bytes == 3
        assert result.error is None

    @pytest.mark.unit
    def test_failure_factory(self) -> None:
        result = DownloadResult.failure("nope")
        assert result.success is False
        assert result.file_path is None
        assert result.size_bytes is None
        assert result.error == "nope"
