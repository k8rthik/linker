"""URL parsing utilities."""

from urllib.parse import urlparse


def extract_domain(url: str) -> str:
    """Return the lowercased hostname of `url`, or empty string on parse failure."""
    if not url:
        return ""
    try:
        normalized = url if url.startswith(("http://", "https://")) else f"https://{url}"
        return urlparse(normalized).netloc or ""
    except Exception:
        return ""
