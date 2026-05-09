"""Video downloader abstraction with a yt-dlp subprocess implementation.

Cache-service-facing protocol so the service can be tested with a fake without
shelling out. The yt-dlp impl uses --print after_move:filepath to capture the
final on-disk path (extension varies per source).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DownloadResult:
    success: bool
    file_path: Optional[Path] = None
    size_bytes: Optional[int] = None
    error: Optional[str] = None

    @classmethod
    def success_(cls, file_path: Path, size_bytes: int) -> "DownloadResult":
        return cls(success=True, file_path=file_path, size_bytes=size_bytes)

    @classmethod
    def failure(cls, error: str) -> "DownloadResult":
        return cls(success=False, error=error)


class VideoDownloader(Protocol):
    """Protocol for video downloaders. Implementations must be thread-safe at the call level."""

    def is_available(self) -> bool: ...

    def download(self, url: str, dest_dir: Path) -> DownloadResult: ...


# Locations to check when PATH is sanitized (e.g. .app bundle launched from Finder
# inherits only /usr/bin:/bin:/usr/sbin:/sbin, missing /opt/homebrew/bin).
_FALLBACK_BIN_DIRS = (
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/opt/local/bin",
    str(Path.home() / ".local" / "bin"),
)


@dataclass
class YtDlpDownloader:
    """Shells out to yt-dlp. Filename templated as <hash>.<ext>; the actual ext is decided by yt-dlp."""

    binary: str = "yt-dlp"
    timeout_seconds: int = 600
    extra_args: tuple = field(default_factory=tuple)

    def _resolve_binary(self) -> Optional[str]:
        """Resolve the yt-dlp binary to an absolute path.

        If `binary` is already an absolute path, use it directly. Otherwise try
        PATH first, then fall back to common Homebrew/MacPorts/user-local
        locations — necessary because PyInstaller `.app` bundles launched from
        Finder don't inherit the user's shell PATH.
        """
        if os.path.isabs(self.binary):
            return self.binary if os.path.exists(self.binary) else None

        on_path = shutil.which(self.binary)
        if on_path is not None:
            return on_path

        for bin_dir in _FALLBACK_BIN_DIRS:
            candidate = os.path.join(bin_dir, self.binary)
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    def is_available(self) -> bool:
        return self._resolve_binary() is not None

    def download(self, url: str, dest_dir: Path) -> DownloadResult:
        resolved = self._resolve_binary()
        if resolved is None:
            return DownloadResult.failure(
                f"yt-dlp binary not found (looked on PATH and in: "
                f"{', '.join(_FALLBACK_BIN_DIRS)})"
            )

        dest_dir.mkdir(parents=True, exist_ok=True)
        url_hash = _stable_url_hash(url)
        output_template = str(dest_dir / f"{url_hash}.%(ext)s")

        cmd = [
            resolved,
            "--no-playlist",
            "--no-warnings",
            "--no-progress",
            "-o",
            output_template,
            "--print",
            "after_move:filepath",
            *self.extra_args,
            url,
        ]

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return DownloadResult.failure(
                f"yt-dlp timeout after {self.timeout_seconds}s"
            )
        except FileNotFoundError:
            return DownloadResult.failure(
                f"yt-dlp binary not found at '{self.binary}' (install with: brew install yt-dlp)"
            )

        if completed.returncode != 0:
            return DownloadResult.failure(_short_error(completed.stderr or completed.stdout))

        printed = (completed.stdout or "").strip().splitlines()
        if not printed:
            return DownloadResult.failure(
                "yt-dlp returned 0 but did not print an output filepath"
            )

        file_path = Path(printed[-1].strip())
        if not file_path.exists():
            return DownloadResult.failure(
                f"yt-dlp succeeded but file not found at expected path: {file_path}"
            )

        return DownloadResult.success_(
            file_path=file_path, size_bytes=file_path.stat().st_size
        )


def _stable_url_hash(url: str) -> str:
    """Deterministic short hash of URL for cache filenames."""
    import hashlib

    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def _short_error(text: str, max_chars: int = 500) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned or "yt-dlp failed with no error output"
    return cleaned[-max_chars:]
