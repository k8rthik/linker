"""Offline cache service.

Owns the lifecycle of cached video files for favorited links:
- Maintains a single-worker download queue (videos are bandwidth-bound; parallel
  downloads waste cycles).
- Mutates Link cache state and asks the repository to persist.
- Is the only writer of files under `cache_dir`; other code reads paths only.

Threading model:
- The main thread calls enqueue/retry/cancel/delete_cached/clear_all/total_size_bytes.
- A single daemon worker thread drains the queue and runs the downloader.
- The Link object's cache_* fields are mutated only by:
    - main thread before handoff (mark_cache_pending)
    - worker thread during processing (mark_cache_downloading/cached/failed)
  We accept this minimal handoff concurrency since persistence is debounced and
  Tk widgets read on the main thread via the on_status_change callback.
"""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Deque, List, Optional, Tuple

from models.link import (
    CACHE_STATUS_CACHED,
    CACHE_STATUS_FAILED,
    Link,
)
from models.profile import Profile
from repositories.profile_repository import ProfileRepository
from utils.video_downloader import VideoDownloader

logger = logging.getLogger(__name__)


StatusChangeCallback = Callable[[str, Link], None]
"""Invoked from the worker thread on every status transition.
   Args: (profile_name, link). UI callers must marshal to the main thread."""


_LOG_BUFFER_SIZE = 500


@dataclass(frozen=True)
class CacheLogEntry:
    """Single observable event in the offline-cache lifecycle."""

    timestamp: float
    level: str  # "info" | "success" | "warn" | "error"
    event: str  # short tag: "queued", "downloading", "cached", "failed", ...
    message: str
    link_name: Optional[str] = None
    link_url: Optional[str] = None
    profile_name: Optional[str] = None


CacheLogCallback = Callable[[CacheLogEntry], None]
"""Invoked on every new log entry. May fire from the worker thread."""


@dataclass(frozen=True)
class _CacheJob:
    profile_name: str
    link: Link


_SENTINEL = _CacheJob(profile_name="", link=None)  # type: ignore[arg-type]


class CacheService:
    def __init__(
        self,
        repository: ProfileRepository,
        downloader: VideoDownloader,
        cache_dir: Path,
        on_status_change: Optional[StatusChangeCallback] = None,
        synchronous: bool = False,
    ) -> None:
        self._repository = repository
        self._downloader = downloader
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._on_status_change = on_status_change
        self._synchronous = synchronous

        self._queue: "queue.Queue[_CacheJob]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._log_lock = threading.Lock()
        self._log_buffer: Deque[CacheLogEntry] = deque(maxlen=_LOG_BUFFER_SIZE)
        self._on_log: Optional[CacheLogCallback] = None
        self._current_job: Optional[Tuple[str, str, str]] = None  # (profile, name, url)
        self._pending_count = 0

        if not synchronous:
            self._start_worker()

    # ---- Public API ----

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def is_downloader_available(self) -> bool:
        return self._downloader.is_available()

    def set_on_status_change(self, callback: Optional[StatusChangeCallback]) -> None:
        """Register or clear the status-change callback. Invoked from the worker thread."""
        self._on_status_change = callback

    def set_on_log(self, callback: Optional[CacheLogCallback]) -> None:
        """Register or clear the log callback. Fires on every new entry; may run on the worker thread."""
        self._on_log = callback

    def get_log_entries(self) -> List[CacheLogEntry]:
        """Return a snapshot of recent log entries (oldest first)."""
        with self._log_lock:
            return list(self._log_buffer)

    def clear_log(self) -> None:
        with self._log_lock:
            self._log_buffer.clear()

    def current_job(self) -> Optional[Tuple[str, str, str]]:
        """(profile_name, link_name, link_url) of the in-flight download, or None."""
        return self._current_job

    def queue_size(self) -> int:
        """Number of jobs waiting in the queue (excludes the in-flight one)."""
        return self._pending_count

    def enqueue_favorites_backfill(self) -> int:
        """Enqueue every favorited link that isn't already cached.

        Used at app startup to catch up favorites created before the cache
        feature shipped, retry transient yt-dlp failures, and unstick links
        left in pending/downloading state by an interrupted session.

        Batches the per-link state mutations into one repository write per
        profile (instead of one per link) and skips the on_status_change
        callback during this phase — the worker thread will fire callbacks
        as it processes jobs anyway, so per-link notifications here would
        only generate redundant UI refreshes.

        No-ops when the downloader is unavailable. Returns the number of
        links enqueued.
        """
        if not self._downloader.is_available():
            self._log(
                "warn",
                "backfill",
                "Skipping favorites backfill: yt-dlp not available",
            )
            return 0

        count = 0
        for profile in self._repository.find_all():
            profile_dirty = False
            for link in profile.all_links:
                if link.favorite and not link.is_cached():
                    link.mark_cache_pending()
                    profile_dirty = True
                    self._log(
                        "info",
                        "queued",
                        "Queued for caching (backfill)",
                        link=link,
                        profile_name=profile.name,
                    )
                    self._submit(_CacheJob(profile_name=profile.name, link=link))
                    count += 1
            if profile_dirty:
                self._repository.update(profile)
        self._log(
            "info",
            "backfill",
            f"Backfill enqueued {count} link{'s' if count != 1 else ''}",
        )
        return count

    def enqueue(self, profile_name: str, link: Link) -> None:
        """Schedule a download. No-op if already cached. Marks failed immediately if downloader unavailable."""
        if link.is_cached():
            self._log(
                "info",
                "skipped",
                "Already cached, skipping enqueue",
                link=link,
                profile_name=profile_name,
            )
            return

        if not self._downloader.is_available():
            err = "yt-dlp not found on PATH (install with: brew install yt-dlp)"
            link.mark_cache_failed(err)
            self._log(
                "error",
                "failed",
                err,
                link=link,
                profile_name=profile_name,
            )
            self._notify_and_persist(profile_name, link)
            return

        link.mark_cache_pending()
        self._log(
            "info",
            "queued",
            "Queued for caching",
            link=link,
            profile_name=profile_name,
        )
        self._notify_and_persist(profile_name, link)
        self._submit(_CacheJob(profile_name=profile_name, link=link))

    def retry(self, profile_name: str, link: Link) -> None:
        """Retry a failed cache. Clears prior error and re-enqueues."""
        self._log(
            "info",
            "retry",
            "Retrying after previous failure",
            link=link,
            profile_name=profile_name,
        )
        link.clear_cache()
        self._notify_and_persist(profile_name, link)
        self.enqueue(profile_name, link)

    def cancel(self, link: Link) -> None:
        """Best-effort cancel for a pending link. Does not interrupt an in-flight download.
        Drains and reinserts non-matching jobs (queue is small, so cost is fine)."""
        removed = 0
        drained = []
        try:
            while True:
                job = self._queue.get_nowait()
                if job.link is link:
                    removed += 1
                    continue
                drained.append(job)
        except queue.Empty:
            pass
        for job in drained:
            self._queue.put(job)
        self._pending_count = max(0, self._pending_count - removed)
        if removed:
            self._log(
                "info",
                "cancelled",
                "Removed from queue (in-flight downloads not interrupted)",
                link=link,
            )

    def delete_cached(self, profile_name: str, link: Link) -> None:
        """Remove the on-disk file for a link and reset its cache state."""
        path = link.cached_path
        if path:
            try:
                Path(path).unlink(missing_ok=True)
                self._log(
                    "info",
                    "deleted",
                    f"Removed cache file {path}",
                    link=link,
                    profile_name=profile_name,
                )
            except OSError as e:
                self._log(
                    "warn",
                    "delete_failed",
                    f"Failed to remove cache file {path}: {e}",
                    link=link,
                    profile_name=profile_name,
                )
        link.clear_cache()
        self._notify_and_persist(profile_name, link)

    def clear_all(self) -> None:
        """Wipe every cache file and reset every link's cache state."""
        removed_files = 0
        for entry in self._cache_dir.iterdir():
            try:
                if entry.is_file():
                    entry.unlink()
                    removed_files += 1
            except OSError as e:
                self._log(
                    "warn",
                    "delete_failed",
                    f"Failed to remove cache file {entry}: {e}",
                )

        reset_links = 0
        for profile in self._repository.find_all():
            mutated = False
            for link in profile.all_links:
                if link.cache_status != "none" or link.cached_path is not None:
                    link.clear_cache()
                    mutated = True
                    reset_links += 1
            if mutated:
                self._repository.update(profile)
        self._log(
            "info",
            "cleared",
            f"Cleared cache: removed {removed_files} file(s), reset {reset_links} link(s)",
        )

    def total_size_bytes(self) -> int:
        total = 0
        for profile in self._repository.find_all():
            for link in profile.all_links:
                if link.cache_size_bytes:
                    total += link.cache_size_bytes
        return total

    def get_cached_path(self, link: Link) -> Optional[Path]:
        """Return the local file path if cached AND the file exists on disk.
        If the file is missing (user deleted it manually), reset the link's
        cache state and return None."""
        if not link.is_cached():
            return None
        path = Path(link.cached_path)  # type: ignore[arg-type]
        if not path.exists():
            link.clear_cache()
            profile_name = self._find_profile_name_for_link(link)
            if profile_name is not None:
                self._notify_and_persist(profile_name, link)
            return None
        return path

    def shutdown(self, timeout: float = 2.0) -> None:
        """Stop the worker thread cleanly. Safe to call multiple times."""
        if self._worker is None:
            return
        self._stop_event.set()
        self._queue.put(_SENTINEL)
        self._worker.join(timeout=timeout)
        self._worker = None

    # ---- Internals ----

    def _log(
        self,
        level: str,
        event: str,
        message: str,
        link: Optional[Link] = None,
        profile_name: Optional[str] = None,
    ) -> None:
        entry = CacheLogEntry(
            timestamp=time.time(),
            level=level,
            event=event,
            message=message,
            link_name=link.name if link is not None else None,
            link_url=link.url if link is not None else None,
            profile_name=profile_name,
        )
        with self._log_lock:
            self._log_buffer.append(entry)

        log_fn = {
            "error": logger.error,
            "warn": logger.warning,
            "success": logger.info,
            "info": logger.info,
        }.get(level, logger.info)
        prefix = f"[{event}]"
        if link is not None:
            log_fn("%s %s — %s (%s)", prefix, message, link.name, link.url)
        else:
            log_fn("%s %s", prefix, message)

        if self._on_log is not None:
            try:
                self._on_log(entry)
            except Exception:  # pragma: no cover — defensive
                logger.exception("Cache log callback raised")

    def _submit(self, job: _CacheJob) -> None:
        if self._synchronous:
            self._process_job(job)
        else:
            self._pending_count += 1
            self._queue.put(job)

    def _start_worker(self) -> None:
        self._worker = threading.Thread(
            target=self._worker_loop, name="CacheWorker", daemon=True
        )
        self._worker.start()

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            job = self._queue.get()
            if job is _SENTINEL:
                return
            self._pending_count = max(0, self._pending_count - 1)
            try:
                self._process_job(job)
            except Exception:  # pragma: no cover — defensive
                logger.exception("Cache worker crashed processing job")
                self._log(
                    "error",
                    "crashed",
                    "Cache worker crashed; see app logs",
                    link=job.link,
                    profile_name=job.profile_name,
                )
                self._current_job = None

    def _process_job(self, job: _CacheJob) -> None:
        link = job.link
        self._current_job = (job.profile_name, link.name, link.url)
        link.mark_cache_downloading()
        self._notify_and_persist(job.profile_name, link)
        started = time.monotonic()
        self._log(
            "info",
            "downloading",
            "Starting download",
            link=link,
            profile_name=job.profile_name,
        )

        result = self._downloader.download(link.url, self._cache_dir)
        elapsed = time.monotonic() - started
        if result.success and result.file_path is not None:
            link.mark_cached(
                path=str(result.file_path),
                size_bytes=result.size_bytes or 0,
            )
            size_mb = (result.size_bytes or 0) / (1024 * 1024)
            self._log(
                "success",
                "cached",
                f"Cached {size_mb:.1f} MB in {elapsed:.1f}s",
                link=link,
                profile_name=job.profile_name,
            )
        else:
            err = result.error or "unknown download error"
            link.mark_cache_failed(err)
            self._log(
                "error",
                "failed",
                f"Download failed after {elapsed:.1f}s: {err}",
                link=link,
                profile_name=job.profile_name,
            )

        self._current_job = None
        self._notify_and_persist(job.profile_name, link)

    def _notify_and_persist(self, profile_name: str, link: Link) -> None:
        profile = self._repository.find_by_name(profile_name)
        if profile is not None:
            self._repository.update(profile)
        if self._on_status_change is not None:
            try:
                self._on_status_change(profile_name, link)
            except Exception:  # pragma: no cover — defensive
                logger.exception("Cache status callback raised")

    def _find_profile_name_for_link(self, link: Link) -> Optional[str]:
        for profile in self._repository.find_all():
            if link in profile.all_links:
                return profile.name
        return None
