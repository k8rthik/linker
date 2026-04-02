"""
Utility for fetching page titles from URLs.
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urlparse


class TitleFetcher:
    """Fetches page titles from URLs."""

    @staticmethod
    def fetch_title(url: str, timeout: int = 5) -> Optional[str]:
        """
        Fetch the title of a webpage from its URL.

        Args:
            url: The URL to fetch the title from
            timeout: Request timeout in seconds

        Returns:
            The page title if successful, None otherwise
        """
        try:
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'

            # Make the request with a timeout
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            response.raise_for_status()

            # Reject titles from cross-page redirects (different path = different page)
            original_path = urlparse(url).path.rstrip('/')
            final_path = urlparse(response.url).path.rstrip('/')
            if original_path != final_path:
                return None

            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try to find the title
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
                # Clean up common title patterns
                title = TitleFetcher._clean_title(title)
                return title

            # Fallback: try og:title meta tag
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                return og_title['content'].strip()

            return None

        except requests.RequestException:
            # Network error, timeout, or HTTP error
            return None
        except Exception:
            # Parsing error or other issue
            return None

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
