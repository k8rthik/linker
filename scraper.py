import time
import requests
import argparse
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup

# ─── Argument Parsing ────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(
    description="Crawl a single domain and list all valid in-domain URLs."
)
parser.add_argument(
    "domain",
    help="The target domain (e.g., example.com) without scheme or path"
)
parser.add_argument(
    "--delay",
    type=float,
    default=1.0,
    help="Seconds to wait between requests (default: 1.0)"
)
parser.add_argument(
    "--user-agent",
    default="MyCrawler/1.0 (+https://your-site.example.com)",
    help="User-Agent string to use for requests"
)
args = parser.parse_args()

DOMAIN = args.domain.lower().strip("/")
SEED_URL = f"https://{DOMAIN}/"
REQUEST_DELAY = args.delay
USER_AGENT = args.user_agent

# ─── Set up robots.txt parser ───────────────────────────────────────────────────

robots_url = f"https://{DOMAIN}/robots.txt"
rp = RobotFileParser()
rp.set_url(robots_url)
rp.read()

# ─── Helper Functions ────────────────────────────────────────────────────────────

def is_same_domain(url: str) -> bool:
    """
    Return True if url’s netloc is exactly the provided DOMAIN (no subdomains).
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.netloc.lower() == DOMAIN

def normalize_link(base: str, link: str) -> str:
    """
    Build absolute URL, strip fragments (#...), and remove trailing slash if not root.
    """
    abs_url = urljoin(base, link)
    abs_url = abs_url.split("#", 1)[0]
    # Strip trailing slash except for the root itself
    if abs_url.endswith("/") and len(abs_url) > len(SEED_URL):
        abs_url = abs_url.rstrip("/")
    return abs_url

# ─── Main Crawler ────────────────────────────────────────────────────────────────

def crawl_domain(seed_url: str):
    seen_urls = {seed_url}
    to_crawl = [seed_url]
    headers = {"User-Agent": USER_AGENT}

    while to_crawl:
        current = to_crawl.pop(0)
        print(f"Crawling: {current}")

        # Check robots.txt permission
        if not rp.can_fetch(USER_AGENT, current):
            print(f"  ↳ Skipping (robots.txt disallows): {current}")
            continue

        try:
            resp = requests.get(current, headers=headers, timeout=10)
        except requests.RequestException as e:
            print(f"  ↳ Failed to fetch {current}: {e}")
            continue

        content_type = resp.headers.get("Content-Type", "")
        if resp.status_code != 200 or "html" not in content_type:
            print(f"  ↳ Skipping (status: {resp.status_code}, type: {content_type})")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            raw_href = a_tag["href"]
            abs_url = normalize_link(current, raw_href)

            parsed = urlparse(abs_url)
            scheme = parsed.scheme.lower()

            # Must be HTTP(S)
            if scheme not in ("http", "https"):
                continue

            # Must stay in same domain
            if not is_same_domain(abs_url):
                continue

            # Check robots.txt for this URL
            if not rp.can_fetch(USER_AGENT, abs_url):
                continue

            if abs_url not in seen_urls:
                seen_urls.add(abs_url)
                to_crawl.append(abs_url)

        time.sleep(REQUEST_DELAY)

    return seen_urls

if __name__ == "__main__":
    all_urls = crawl_domain(SEED_URL)
    print("\nFound URLs:")
    for url in sorted(all_urls):
        print(url)
