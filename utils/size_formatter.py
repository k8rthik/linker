"""Human-readable byte size formatting."""

from __future__ import annotations

_UNITS = ["B", "KB", "MB", "GB", "TB"]


def format_size_bytes(n: int) -> str:
    """Format a byte count as a short human-readable string.

    Bytes are shown without a decimal; KB and above use one decimal place.
    Negative values are treated as zero (we never want to display "-50 MB").
    """
    if n <= 0:
        return "0 B"
    size = float(n)
    for unit in _UNITS:
        if size < 1024 or unit == _UNITS[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} {_UNITS[-1]}"
