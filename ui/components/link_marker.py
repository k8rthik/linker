"""Format the combined favorite/cache marker for a link row.

Lives in its own tiny module so the formatter is unit-testable without pulling
in Tkinter (the LinkListView that consumes it does require Tk).
"""

from __future__ import annotations

from models.link import (
    CACHE_STATUS_CACHED,
    CACHE_STATUS_DOWNLOADING,
    CACHE_STATUS_FAILED,
    CACHE_STATUS_PENDING,
    Link,
)


def format_link_marker(link: Link) -> str:
    """Return the glyph string to render in the link list's leading column.

    Combines the favorite indicator (★) with a cache-state glyph:
      - ⬇  cached and openable offline
      - …  pending or downloading
      - ⚠  download failed
      - (none) when cache_status is "none"
    """
    parts = []
    if link.favorite:
        parts.append("★")
    status = link.cache_status
    if status == CACHE_STATUS_CACHED:
        parts.append("⬇")
    elif status in (CACHE_STATUS_PENDING, CACHE_STATUS_DOWNLOADING):
        parts.append("…")
    elif status == CACHE_STATUS_FAILED:
        parts.append("⚠")
    return "".join(parts)
