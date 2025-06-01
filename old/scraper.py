import time
import requests
import argparse
import json
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup

# ─── Constants ───────────────────────────────────────────────────────────────────

DATA_FILE = "links.json"

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
    default="*",
    help="User-Agent string to use for requests (default: * for generic bot)"
)
parser.add_argument(
    "--save-to-db",
    action="store_true",
    help="Save scraped URLs to the links.json database"
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable debug output for troubleshooting"
)
args = parser.parse_args()

DOMAIN = args.domain.lower().strip("/")
SEED_URL = f"https://{DOMAIN}/"
REQUEST_DELAY = args.delay
USER_AGENT = args.user_agent
SAVE_TO_DB = args.save_to_db
DEBUG = args.debug

# ─── Set up robots.txt parser ───────────────────────────────────────────────────

robots_url = f"https://{DOMAIN}/robots.txt"
rp = RobotFileParser()
rp.set_url(robots_url)

if DEBUG:
    print(f"🤖 Fetching robots.txt from: {robots_url}")

try:
    rp.read()
    if DEBUG:
        print(f"✅ Successfully read robots.txt")
        print(f"🔍 User-Agent being used: '{USER_AGENT}'")
        
        # Debug: Print the actual robots.txt content
        try:
            robots_response = requests.get(robots_url, timeout=10)
            if robots_response.status_code == 200:
                print(f"📄 robots.txt content:")
                print("=" * 50)
                print(robots_response.text)
                print("=" * 50)
            else:
                print(f"❌ Could not fetch robots.txt for debugging (status: {robots_response.status_code})")
        except Exception as e:
            print(f"❌ Error fetching robots.txt for debugging: {e}")
            
        # Test a few URLs to see what the parser thinks
        test_urls = [
            f"https://{DOMAIN}/",
            f"https://{DOMAIN}/sitemap.xml",
            f"https://{DOMAIN}/wp-admin/",
            f"https://{DOMAIN}/some-page/"
        ]
        print("🧪 Testing robots.txt permissions for sample URLs:")
        for test_url in test_urls:
            can_fetch = rp.can_fetch(USER_AGENT, test_url)
            print(f"  {test_url} -> {'✅ ALLOWED' if can_fetch else '❌ DISALLOWED'}")
        
except Exception as e:
    if DEBUG:
        print(f"❌ Failed to read robots.txt: {e}")
    # Continue anyway - if we can't read robots.txt, assume everything is allowed

# ─── Link Manager Integration ───────────────────────────────────────────────────

def load_links():
    """Load existing links from the database"""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r") as f:
            links = json.load(f)
        
        # Add missing fields for backward compatibility
        for link in links:
            if "date_added" not in link:
                link["date_added"] = datetime.now().isoformat()
            if "last_opened" not in link:
                link["last_opened"] = None
        
        return links
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_links(links):
    """Save links to the database"""
    with open(DATA_FILE, "w") as f:
        json.dump(links, f, indent=4)

def add_urls_to_db(urls):
    """Add new URLs to the link database, avoiding duplicates"""
    existing_links = load_links()
    existing_urls = {link["url"] for link in existing_links}
    current_time = datetime.now().isoformat()
    
    new_links = []
    for url in urls:
        if url not in existing_urls:
            new_links.append({
                "name": url,
                "url": url,
                "favorite": False,
                "date_added": current_time,
                "last_opened": None
            })
    
    if new_links:
        existing_links.extend(new_links)
        save_links(existing_links)
        print(f"\n✅ Added {len(new_links)} new URLs to links.json database")
        print("New URLs added:")
        for link in new_links:
            print(f"  - {link['url']}")
    else:
        print("\nℹ️  No new URLs to add (all URLs already exist in database)")
    
    return len(new_links)

# ─── Helper Functions ────────────────────────────────────────────────────────────

def is_robots_txt_working_correctly():
    """
    Test if robots.txt parser is working correctly by checking if it allows
    at least some basic URLs that should typically be allowed.
    """
    test_urls = [
        f"https://{DOMAIN}/",
        f"https://{DOMAIN}/index.html",
        f"https://{DOMAIN}/sitemap.xml",
    ]
    
    allowed_count = 0
    for url in test_urls:
        if rp.can_fetch(USER_AGENT, url):
            allowed_count += 1
    
    # If none of the basic URLs are allowed, the parser might be broken
    # (unless the site explicitly disallows everything, which is rare)
    return allowed_count > 0

def can_fetch_url(url: str) -> bool:
    """
    Enhanced robots.txt checking with fallback logic for broken parsers.
    """
    try:
        # First try the normal robots.txt check
        can_fetch = rp.can_fetch(USER_AGENT, url)
        
        # If the parser seems to be blocking everything incorrectly,
        # apply manual logic based on common robots.txt patterns
        if not can_fetch and not is_robots_txt_working_correctly():
            if DEBUG:
                print(f"  🔧 robots.txt parser seems broken, applying manual logic for: {url}")
            
            # Manual check: if URL doesn't match explicit Disallow patterns, allow it
            parsed_url = urlparse(url)
            path = parsed_url.path
            
            # Common patterns that are typically disallowed
            disallowed_patterns = [
                '/wp-admin/',
                '/admin/',
                '/private/',
                '/cgi-bin/',
            ]
            
            # Check if path starts with any disallowed pattern
            for pattern in disallowed_patterns:
                if path.startswith(pattern):
                    return False
            
            # If no disallow pattern matches, allow the URL
            return True
        
        return can_fetch
        
    except Exception as e:
        if DEBUG:
            print(f"  ❌ Error checking robots.txt for {url}: {e}")
        # If robots.txt check fails, be conservative and allow
        return True

def is_same_domain(url: str) -> bool:
    """
    Return True if url's netloc is exactly the provided DOMAIN (no subdomains).
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
        if not can_fetch_url(current):
            if DEBUG:
                print(f"  🤖 robots.txt check for '{current}' with user-agent '{USER_AGENT}': DISALLOWED")
            print(f"  ↳ Skipping (robots.txt disallows): {current}")
            continue
        elif DEBUG:
            print(f"  🤖 robots.txt check for '{current}' with user-agent '{USER_AGENT}': ALLOWED")

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
            if not can_fetch_url(abs_url):
                continue

            if abs_url not in seen_urls:
                seen_urls.add(abs_url)
                to_crawl.append(abs_url)

        time.sleep(REQUEST_DELAY)

    return seen_urls

if __name__ == "__main__":
    print(f"🔍 Starting crawl of domain: {DOMAIN}")
    all_urls = crawl_domain(SEED_URL)
    
    print(f"\n📊 Crawl Summary:")
    print(f"Found {len(all_urls)} URLs on {DOMAIN}")
    
    print("\nFound URLs:")
    for url in sorted(all_urls):
        print(url)
    
    if SAVE_TO_DB:
        add_urls_to_db(all_urls)
    else:
        print(f"\n💡 Tip: Use --save-to-db flag to automatically add these URLs to your links.json database")
