"""Resolve fyptt.to article URLs to their direct stream URLs.

yt-dlp doesn't natively support fyptt.to, so we walk the embed chain ourselves:

    article page  -->  iframe to fypttstr.php  -->  <source src="stream.fyptt.to/...mp4">

The stream URL is token-signed and short-lived, so resolution must happen
immediately before download (don't cache the resolved URL).
"""

from __future__ import annotations

import html
import logging
import re
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
_FYPTT_HOSTS = frozenset({"fyptt.to", "www.fyptt.to"})

# Article page -> iframe URL pointing at the streamer endpoint. Several
# known variants exist (`fypttstr.php` plain player, `fypttjwstr.php`
# JWPlayer + direct mp4, `fypttjwstrhls.php` JWPlayer + HLS), and the
# site has shipped new ones over time. Match any `fyptt[…].php` under
# fyptt.to with a `fileid=` query — that's robust to new variants
# without us having to enumerate suffixes. Match either `src=` or
# `data-src-no-ap=` so we work regardless of lazy-loading state.
_IFRAME_PATTERN = re.compile(
    r'(?:data-src-no-ap|src)=["\']'
    r'(https://fyptt\.to/fyptt[a-z]*\.php\?[^"\']*fileid=[^"\']+)'
    r'["\']'
)

# Inside the iframe response, the actual stream URL appears as either
# `<source src="...">` (plain player) or `file:"..."` (JWPlayer config).
_SOURCE_PATTERNS = (
    re.compile(
        r'<source\s+[^>]*src=["\']'
        r'(https://stream\.fyptt\.to/[^"\']+)'
        r'["\']'
    ),
    re.compile(
        r'file\s*:\s*["\']'
        r'(https://stream\.fyptt\.to/[^"\']+)'
        r'["\']'
    ),
)


def is_fyptt_url(url: str) -> bool:
    """True iff the URL is on the fyptt.to article domain."""
    try:
        return urlparse(url).netloc.lower() in _FYPTT_HOSTS
    except (ValueError, AttributeError):
        return False


def resolve_fyptt_stream_url(
    article_url: str, timeout: float = 10.0
) -> Optional[str]:
    """Resolve a fyptt.to article URL to its direct stream URL.

    Returns None on any failure (network error, missing iframe, missing source).
    Already-direct stream URLs (stream.fyptt.to) are returned unchanged so the
    function is safe to call indiscriminately.
    """
    if "stream.fyptt.to" in article_url:
        return article_url
    if not is_fyptt_url(article_url):
        return None

    headers = {"User-Agent": _USER_AGENT}

    try:
        article_resp = requests.get(article_url, headers=headers, timeout=timeout)
        article_resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(
            "fyptt resolver: article fetch failed for %s: %s", article_url, e
        )
        return None

    iframe_match = _IFRAME_PATTERN.search(article_resp.text)
    if not iframe_match:
        logger.warning("fyptt resolver: no iframe found at %s", article_url)
        return None
    # html.unescape collapses both &amp; and numeric entities like &#038; to &.
    iframe_url = html.unescape(iframe_match.group(1))

    try:
        iframe_resp = requests.get(
            iframe_url,
            headers={**headers, "Referer": article_url},
            timeout=timeout,
        )
        iframe_resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(
            "fyptt resolver: iframe fetch failed for %s: %s", iframe_url, e
        )
        return None

    for pattern in _SOURCE_PATTERNS:
        match = pattern.search(iframe_resp.text)
        if match:
            return html.unescape(match.group(1))

    logger.warning(
        "fyptt resolver: no stream URL found in iframe at %s", iframe_url
    )
    return None
