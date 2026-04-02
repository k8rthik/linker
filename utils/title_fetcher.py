"""
Utility for fetching page titles from URLs.
"""

import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Tuple, Callable
from urllib.parse import urlparse


# Module-level persistent session for connection pooling.
# Reuses TCP connections across fetches to the same domain.
_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    """Return a shared session with connection pooling."""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # Pool size matches our max concurrent workers
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=1,
        )
        _session.mount('https://', adapter)
        _session.mount('http://', adapter)
    return _session


class TitleFetcher:
    """Fetches page titles from URLs."""

    # Default concurrency for batch operations
    MAX_WORKERS = 15

    @staticmethod
    def fetch_title(url: str, timeout: tuple = (3, 5)) -> Optional[str]:
        """
        Fetch the title of a webpage from its URL.

        Args:
            url: The URL to fetch the title from
            timeout: (connect_timeout, read_timeout) in seconds

        Returns:
            The page title if successful, None otherwise
        """
        try:
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'

            session = _get_session()
            response = session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()

            # Reject titles from cross-page redirects (different path = different page)
            original_path = urlparse(url).path.rstrip('/')
            final_path = urlparse(response.url).path.rstrip('/')
            if original_path != final_path:
                return None

            # Skip non-HTML responses early
            content_type = response.headers.get('Content-Type', '')
            if 'html' not in content_type:
                return None

            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try to find the title
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
                title = TitleFetcher._clean_title(title)
                return title

            # Fallback: try og:title meta tag
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                return TitleFetcher._clean_title(og_title['content'].strip())

            return None

        except requests.RequestException:
            return None
        except Exception:
            return None

    @staticmethod
    def fetch_titles_concurrent(
        urls: List[str],
        on_result: Optional[Callable[[str, Optional[str]], None]] = None,
        max_workers: Optional[int] = None,
    ) -> List[Tuple[str, str]]:
        """
        Fetch titles for multiple URLs concurrently using a thread pool.

        Args:
            urls: List of URLs to fetch
            on_result: Optional callback(url, title_or_none) called as each
                       fetch completes. Invoked from worker threads — caller
                       must schedule UI updates via root.after().
            max_workers: Override default concurrency (default: MAX_WORKERS)

        Returns:
            List of (url, title) tuples for successful fetches.
        """
        workers = max_workers or TitleFetcher.MAX_WORKERS
        results: List[Tuple[str, str]] = []

        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_url = {
                pool.submit(TitleFetcher.fetch_title, url): url
                for url in urls
            }

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    title = future.result()
                except Exception:
                    title = None

                if on_result:
                    on_result(url, title)

                if title:
                    results.append((url, title))

        return results

    @staticmethod
    def _clean_title(title: str) -> str:
        """Clean up common title patterns."""
        # Remove excessive whitespace
        title = ' '.join(title.split())

        # Limit length
        max_length = 200
        if len(title) > max_length:
            title = title[:max_length] + '...'

        return title

    @staticmethod
    def get_domain_name(url: str) -> str:
        """Extract domain name from URL for fallback naming."""
        try:
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain if domain else url
        except Exception:
            return url

    @staticmethod
    def should_fetch_title(url: str, current_name: str) -> bool:
        """
        Determine if we should fetch a title for this link.

        Only fetches if the current name appears to be auto-generated or inadequate:
        - Name is exactly the URL
        - Name is just the domain
        - Name is empty or very short (< 3 chars)
        - Name looks like a URL (contains :// or starts with www.)

        Args:
            url: The link's URL
            current_name: The current name of the link

        Returns:
            True if title should be fetched, False otherwise
        """
        if not current_name:
            return True

        # Normalize for comparison
        name_lower = current_name.strip().lower()
        url_lower = url.strip().lower()

        # Name is exactly the URL
        if name_lower == url_lower:
            return True

        # Name is the URL without protocol
        url_without_protocol = url_lower.replace('https://', '').replace('http://', '')
        if name_lower == url_without_protocol:
            return True

        # Name is just the domain
        domain = TitleFetcher.get_domain_name(url).lower()
        if name_lower == domain:
            return True

        # Name is very short (likely inadequate)
        if len(current_name.strip()) < 3:
            return True

        # Name looks like a URL itself
        if '://' in current_name or current_name.startswith('www.'):
            return True

        # Name contains the full URL (sometimes happens with copy-paste)
        if url_lower in name_lower:
            return True

        # Otherwise, respect the user's custom name
        return False
