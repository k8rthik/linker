"""ISO-8601 date parsing utilities."""

from datetime import datetime
from typing import Optional


def safe_parse_iso(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 string into a datetime, or return None on any failure."""
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, AttributeError):
        return None
