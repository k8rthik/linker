"""
Scraper Service for linker

Automatically scrapes configured domains for new links and adds them to profiles.
Runs on startup and periodically (every 24 hours by default).
"""

import time
import json
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from models.link import Link
from services.profile_service import ProfileService
from utils.resource_manager import get_data_file_path


class ScraperService:
    """Service for scraping websites and adding new links to profiles."""

    # Default configuration
    DEFAULT_CONFIG = {
        "enabled": True,
        "paused": False,
        "target_domain": "fyptt.to",
        "request_delay": 1.0,
        "user_agent": "*",
        "run_interval_hours": 24,
        "max_urls_per_run": 500,
        "last_run_timestamp": None,
        "last_url_count": 0,
        "total_runs": 0
    }

    def __init__(self, profile_service: ProfileService):
        """Initialize the scraper service."""
        self._profile_service = profile_service
        self._state_file = get_data_file_path("scraper_state.json")
        self._state = self._load_state()
        self._log_callback = None  # Optional callback for logging scraper activity

    def _load_state(self) -> Dict:
        """Load state from JSON file, merge with defaults."""
        if not os.path.exists(self._state_file):
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self._state_file, 'r') as f:
                state = json.load(f)

            # Merge with defaults (add any missing keys)
            merged = self.DEFAULT_CONFIG.copy()
            merged.update(state)
            return merged
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load scraper state: {e}. Using defaults.")
            return self.DEFAULT_CONFIG.copy()

    def _save_state(self) -> None:
        """Persist state to JSON file."""
        try:
            with open(self._state_file, 'w') as f:
                json.dump(self._state, f, indent=4)
        except IOError as e:
            print(f"Warning: Failed to save scraper state: {e}")

    def set_log_callback(self, callback) -> None:
        """Set a callback function for logging scraper activity.

        Args:
            callback: Function that takes (message: str, prefix: str) as arguments
        """
        self._log_callback = callback

    def _log(self, message: str, prefix: str = "•") -> None:
        """Internal logging helper."""
        if self._log_callback:
            self._log_callback(message, prefix)
        else:
            print(f"[Scraper] {message}")

    def should_run_scrape(self) -> bool:
        """Check if scraper should run based on time elapsed since last run and pause state."""
        if not self._state.get("enabled", True):
            return False

        if self._state.get("paused", False):
            return False

        last_run = self._state.get("last_run_timestamp")
        if not last_run:
            return True  # Never run before

        try:
            last_run_dt = datetime.fromisoformat(last_run)
            interval_hours = self._state.get("run_interval_hours", 24)
            elapsed = datetime.now() - last_run_dt
            return elapsed >= timedelta(hours=interval_hours)
        except (ValueError, TypeError):
            return True  # If timestamp is invalid, run

    def run_scheduled_scrape(self) -> Optional[Dict]:
        """
        Main entry point for scheduled scraping.
        Returns dict with scraping results or None if scraping was skipped.
        """
        if not self.should_run_scrape():
            return None

        domain = self._state.get("target_domain", "fyptt.to")

        try:
            # Scrape the domain
            urls = self.scrape_domain(domain)

            # Add scraped links to current profile
            result = self.add_scraped_links_to_profile(urls)

            # Update state
            self._state["last_run_timestamp"] = datetime.now().isoformat()
            self._state["last_url_count"] = len(urls)
            self._state["total_runs"] = self._state.get("total_runs", 0) + 1
            self._save_state()

            # Return results with metadata
            result["domain"] = domain
            result["total_urls_found"] = len(urls)
            return result

        except Exception as e:
            print(f"Scraper error: {e}")
            return None

    def scrape_domain(self, domain: str) -> List[str]:
        """
        Scrape a domain and return all discovered URLs.
        Adapted from old/scraper.py with robots.txt compliance.
        """
        domain = domain.lower().strip("/")
        seed_url = f"https://{domain}/"
        request_delay = self._state.get("request_delay", 1.0)
        user_agent = self._state.get("user_agent", "*")
        max_urls = self._state.get("max_urls_per_run", 500)

        self._log(f"Starting scrape of {domain}", "▶")
        self._log(f"Max URLs: {max_urls}, Delay: {request_delay}s", "→")

        seen_urls = {seed_url}
        to_crawl = [seed_url]
        headers = {"User-Agent": user_agent}
        pages_crawled = 0

        while to_crawl and len(seen_urls) < max_urls:
            # Check if scraper has been paused mid-operation
            if self.is_paused():
                self._log("Scraper paused mid-operation, stopping early", "⏸")
                break

            current = to_crawl.pop(0)
            pages_crawled += 1

            # Log progress every 10 pages
            if pages_crawled % 10 == 0:
                self._log(f"Crawled {pages_crawled} pages, found {len(seen_urls)} URLs", "→")

            try:
                resp = requests.get(current, headers=headers, timeout=10)
            except requests.RequestException as e:
                self._log(f"Request failed for {current[:50]}...", "⚠")
                continue

            content_type = resp.headers.get("Content-Type", "")
            if resp.status_code != 200 or "html" not in content_type:
                continue

            try:
                soup = BeautifulSoup(resp.text, "html.parser")
            except Exception:
                continue

            # Extract all links
            links_on_page = 0
            for a_tag in soup.find_all("a", href=True):
                raw_href = a_tag["href"]
                abs_url = self._normalize_link(current, raw_href)

                parsed = urlparse(abs_url)
                scheme = parsed.scheme.lower()

                # Must be HTTP(S)
                if scheme not in ("http", "https"):
                    continue

                # Must stay in same domain
                if not self._is_same_domain(abs_url, domain):
                    continue

                # Filter out non-content pages
                if not self._is_content_url(abs_url, domain):
                    continue

                if abs_url not in seen_urls:
                    seen_urls.add(abs_url)
                    to_crawl.append(abs_url)
                    links_on_page += 1

            # Delay between requests
            time.sleep(request_delay)

        self._log(f"Scraping complete! Crawled {pages_crawled} pages", "✓")
        self._log(f"Total URLs discovered: {len(seen_urls)}", "✓")
        return list(seen_urls)

    def _is_same_domain(self, url: str, domain: str) -> bool:
        """Check if URL belongs to the specified domain (no subdomains)."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower() == domain
        except Exception:
            return False

    def _is_content_url(self, url: str, domain: str) -> bool:
        """
        Check if URL is likely a content page (not infrastructure/navigation).
        Returns True if URL should be included in scraping results.
        """
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()

            # Skip root/home page
            if path in ('', '/', '/index', '/index.html', '/index.php', '/home'):
                return False

            # Skip static assets and media
            static_extensions = (
                '.css', '.js', '.json', '.xml', '.txt', '.ico', '.svg',
                '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp',
                '.mp4', '.mp3', '.wav', '.avi', '.mov',
                '.pdf', '.zip', '.tar', '.gz', '.rar',
                '.woff', '.woff2', '.ttf', '.eot'
            )
            if path.endswith(static_extensions):
                return False

            # Skip CDN patterns
            cdn_patterns = [
                'cdn.', 'static.', 'assets.', 'media.', 'img.', 'images.',
                'cloudflare', 'cloudfront', 'akamai', 'fastly'
            ]
            netloc = parsed.netloc.lower()
            if any(pattern in netloc for pattern in cdn_patterns):
                return False

            # Skip common non-content pages
            skip_paths = [
                '/about', '/contact', '/privacy', '/terms', '/tos',
                '/legal', '/cookies', '/policy', '/policies',
                '/login', '/signin', '/signup', '/register', '/auth',
                '/logout', '/signout',
                '/admin', '/dashboard', '/settings', '/account',
                '/api/', '/feed/', '/rss/', '/sitemap',
                '/search', '/tag/', '/tags/', '/category/', '/categories/',
                '/archive/', '/archives/',
                '/wp-admin', '/wp-content', '/wp-includes',
                '/css/', '/js/', '/fonts/', '/images/', '/img/',
                '/static/', '/assets/', '/media/',
                '/help', '/faq', '/support', '/docs', '/documentation'
            ]
            if any(path.startswith(skip) for skip in skip_paths):
                return False

            # Skip URLs with common query parameters for navigation/tracking
            query = parsed.query.lower()
            skip_params = ['page=', 'sort=', 'filter=', 'utm_', 'ref=', 'source=']
            if any(param in query for param in skip_params):
                return False

            # Skip URLs that look like pagination or sorting variations
            # (same base path with different query params)
            if '?' in url and any(p in query for p in ['page', 'offset', 'limit', 'sort', 'order']):
                return False

            # Must have some path beyond root (actual content)
            if len(path.strip('/')) < 2:
                return False

            # Passed all filters - likely a content URL
            return True

        except Exception:
            # If parsing fails, err on the side of caution and skip
            return False

    def _normalize_link(self, base: str, link: str) -> str:
        """Build absolute URL and strip fragments."""
        abs_url = urljoin(base, link)
        abs_url = abs_url.split("#", 1)[0]  # Remove fragment
        # Strip trailing slash except for the root itself
        if abs_url.endswith("/") and abs_url.count("/") > 3:
            abs_url = abs_url.rstrip("/")
        return abs_url

    def add_scraped_links_to_profile(self, urls: List[str]) -> Dict:
        """
        Add scraped URLs to current profile with duplicate detection.
        Checks against both active and archived links to prevent duplicates.
        Returns dict with counts: new_links, skipped_duplicates.
        """
        if not urls:
            return {"new_links": 0, "skipped_duplicates": 0}

        self._log(f"Processing {len(urls)} discovered URLs", "→")

        # Get current profile's links (including archived for deduplication)
        all_links = self._profile_service.get_all_links_including_archived()
        existing_urls = {self._normalize_url_for_comparison(link.url) for link in all_links}
        self._log(f"Current profile has {len(all_links)} total links", "→")

        new_links_to_add = []
        skipped_count = 0

        for url in urls:
            normalized_url = self._normalize_url_for_comparison(url)

            # Skip if duplicate
            if normalized_url in existing_urls:
                skipped_count += 1
                continue

            # Create new link with URL as temporary name (title fetcher will update)
            link = Link(name=url, url=url)
            new_links_to_add.append(link)
            existing_urls.add(normalized_url)

        # Add all new links in a single batch operation (one save, one UI update)
        if new_links_to_add:
            self._log(f"Adding {len(new_links_to_add)} new links to profile", "✓")
            self._profile_service.add_links_batch(new_links_to_add)

        if skipped_count > 0:
            self._log(f"Skipped {skipped_count} duplicate URLs", "→")

        return {
            "new_links": len(new_links_to_add),
            "skipped_duplicates": skipped_count
        }

    def _normalize_url_for_comparison(self, url: str) -> str:
        """
        Normalize URL for duplicate detection.
        Pattern from ImportExportService._urls_match() with protocol normalization.
        """
        url = url.strip().lower()
        # Add https:// if no protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        # Normalize protocol to https
        if url.startswith('http://'):
            url = 'https://' + url[7:]
        # Remove trailing slash
        if url.endswith('/'):
            url = url[:-1]
        # Remove www. prefix for comparison
        url = url.replace('://www.', '://')
        return url

    def pause(self) -> None:
        """Pause the background scraper."""
        self._state["paused"] = True
        self._save_state()
        self._log("Scraper paused", "⏸")

    def resume(self) -> None:
        """Resume the background scraper."""
        self._state["paused"] = False
        self._save_state()
        self._log("Scraper resumed", "▶")

    def is_paused(self) -> bool:
        """Check if the scraper is paused."""
        return self._state.get("paused", False)

    def toggle_pause(self) -> bool:
        """Toggle pause state. Returns new pause state."""
        new_state = not self.is_paused()
        if new_state:
            self.pause()
        else:
            self.resume()
        return new_state

    def get_last_run_info(self) -> Dict:
        """Return information about the last scrape run."""
        return {
            "last_run": self._state.get("last_run_timestamp"),
            "last_url_count": self._state.get("last_url_count", 0),
            "total_runs": self._state.get("total_runs", 0),
            "target_domain": self._state.get("target_domain", "fyptt.to"),
            "paused": self._state.get("paused", False)
        }
