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
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

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

    def enqueue_favorites_backfill(self) -> int:
        """Enqueue every favorited link that isn't already cached.

        Used at app startup to catch up favorites created before the cache
        feature shipped, retry transient yt-dlp failures, and unstick links
        left in pending/downloading state by an interrupted session.

        No-ops when the downloader is unavailable — refusing to mark every
        favorite as failed avoids wiping useful prior cache_error context and
        avoids spamming persistence at startup. Returns the number of links
        enqueued.
        """
        if not self._downloader.is_available():
            logger.info(
                "Skipping favorites backfill: downloader unavailable"
            )
            return 0

        count = 0
        for profile in self._repository.find_all():
            for link in profile.all_links:
                if link.favorite and not link.is_cached():
                    self.enqueue(profile.name, link)
                    count += 1
        return count

    def enqueue(self, profile_name: str, link: Link) -> None:
        """Schedule a download. No-op if already cached. Marks failed immediately if downloader unavailable."""
        if link.is_cached():
            return

        if not self._downloader.is_available():
            link.mark_cache_failed(
                "yt-dlp not found on PATH (install with: brew install yt-dlp)"
            )
            self._notify_and_persist(profile_name, link)
            return

        link.mark_cache_pending()
        self._notify_and_persist(profile_name, link)
        self._submit(_CacheJob(profile_name=profile_name, link=link))

    def retry(self, profile_name: str, link: Link) -> None:
        """Retry a failed cache. Clears prior error and re-enqueues."""
        link.clear_cache()
        self._notify_and_persist(profile_name, link)
        self.enqueue(profile_name, link)

    def cancel(self, link: Link) -> None:
        """Best-effort cancel for a pending link. Does not interrupt an in-flight download.
        Drains and reinserts non-matching jobs (queue is small, so cost is fine)."""
        drained = []
        try:
            while True:
                job = self._queue.get_nowait()
                if job.link is link:
                    continue
                drained.append(job)
        except queue.Empty:
            pass
        for job in drained:
            self._queue.put(job)

    def delete_cached(self, profile_name: str, link: Link) -> None:
        """Remove the on-disk file for a link and reset its cache state."""
        path = link.cached_path
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError as e:
                logger.warning("Failed to remove cache file %s: %s", path, e)
        link.clear_cache()
        self._notify_and_persist(profile_name, link)

    def clear_all(self) -> None:
        """Wipe every cache file and reset every link's cache state."""
        for entry in self._cache_dir.iterdir():
            try:
                if entry.is_file():
                    entry.unlink()
            except OSError as e:
                logger.warning("Failed to remove cache file %s: %s", entry, e)

        for profile in self._repository.find_all():
            mutated = False
            for link in profile.all_links:
                if link.cache_status != "none" or link.cached_path is not None:
                    link.clear_cache()
                    mutated = True
            if mutated:
                self._repository.update(profile)

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

    def _submit(self, job: _CacheJob) -> None:
        if self._synchronous:
            self._process_job(job)
        else:
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
            try:
                self._process_job(job)
            except Exception:  # pragma: no cover — defensive
                logger.exception("Cache worker crashed processing job")

    def _process_job(self, job: _CacheJob) -> None:
        link = job.link
        link.mark_cache_downloading()
        self._notify_and_persist(job.profile_name, link)

        result = self._downloader.download(link.url, self._cache_dir)
        if result.success and result.file_path is not None:
            link.mark_cached(
                path=str(result.file_path),
                size_bytes=result.size_bytes or 0,
            )
        else:
            link.mark_cache_failed(result.error or "unknown download error")

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
