# Smart Title Fetching

## Overview

linker now intelligently fetches page titles for your links automatically, but **only** when the current name appears to be auto-generated or inadequate. This means your manually-named links are **always respected**.

## How It Works

### Smart Detection Algorithm

The system analyzes each link's name and URL to determine if title fetching is needed. It will **only** fetch titles when:

1. **Name is exactly the URL**
   - `name: "https://github.com/anthropics/claude-code"`
   - `url: "https://github.com/anthropics/claude-code"`
   - ✅ Will fetch

2. **Name is the URL without protocol**
   - `name: "github.com/anthropics/claude-code"`
   - `url: "https://github.com/anthropics/claude-code"`
   - ✅ Will fetch

3. **Name is just the domain**
   - `name: "github.com"`
   - `url: "https://github.com/anthropics/claude-code"`
   - ✅ Will fetch

4. **Name is very short (< 3 characters)**
   - `name: "gh"`
   - `url: "https://github.com/anthropics/claude-code"`
   - ✅ Will fetch

5. **Name looks like a URL**
   - `name: "www.example.com"` or contains `"://"`
   - ✅ Will fetch

6. **Name contains the full URL**
   - `name: "Check this out: https://example.com"`
   - `url: "https://example.com"`
   - ✅ Will fetch

### What It Won't Touch

The system **will NOT** fetch titles when:

- Name is clearly user-provided and descriptive
  - `name: "My favorite article about Python"` ❌ Won't fetch
- Name is a custom label
  - `name: "Work Project"` ❌ Won't fetch
- Name has been manually edited
  - `name: "GitHub - Claude Code Repo"` ❌ Won't fetch

**Bottom line:** If you named it yourself, the system respects it!

## When Title Fetching Happens

### 1. When Adding New Links

**User Action:**
```
1. Click "Add Links"
2. Paste URLs:
   https://github.com/anthropics/claude-code
   https://python.org
3. Click OK
```

**What Happens:**
```
1. Links are added immediately with URL as temporary name
   ✓ Link added: "https://github.com/anthropics/claude-code"
   ✓ Link added: "https://python.org"

2. Background thread starts (non-blocking):
   - Checks: Should we fetch for "https://github.com/anthropics/claude-code"?
   - Decision: YES (name is the URL)
   - Fetches: "anthropics/claude-code: Official Claude Code repository"

   - Checks: Should we fetch for "https://python.org"?
   - Decision: YES (name is the URL)
   - Fetches: "Welcome to Python.org"

3. Titles update automatically in the UI
   ✓ Updated: "anthropics/claude-code: Official Claude Code repository"
   ✓ Updated: "Welcome to Python.org"
```

**Timeline:**
- **0ms:** Links appear with URL as name (instant feedback)
- **100-5000ms:** Titles update as they're fetched (varies by site)
- **No blocking:** You can keep working while fetching happens

### 2. On App Startup (Retroactive)

**What Happens:**
```
1. App starts normally
2. UI loads completely
3. After 1 second delay:
   - Background scan starts
   - Finds all links with URL-based names
   - Fetches titles for them
   - Updates quietly in background
```

**Example:**
```
Before scan (old links in your database):
- "https://example.com" → Will be updated
- "github.com" → Will be updated
- "My custom name" → Left alone ✓

After scan:
- "Example Domain - Official Site"
- "GitHub: Where the world builds software"
- "My custom name" → Still unchanged ✓
```

### 3. Manual Scan (Ctrl/Cmd+Shift+T)

**User Action:**
```
Press Ctrl+Shift+T (or Cmd+Shift+T on Mac)
```

**What Happens:**
```
1. System scans all links in current profile
2. Counts how many need title updates
3. Shows confirmation dialog:
   ┌─────────────────────────────────────────┐
   │ Scan Titles                             │
   ├─────────────────────────────────────────┤
   │ Found 15 link(s) that could use better  │
   │ titles. Fetch titles from the web?      │
   │                                         │
   │ (This will only update links with       │
   │  URL-based names)                       │
   │                                         │
   │         [Yes]  [No]                     │
   └─────────────────────────────────────────┘

4. If Yes: Fetches in background
5. Shows progress message:
   "Fetching titles for 15 link(s) in background..."
```

**Use Cases:**
- After bulk importing links
- Cleaning up old links with URL names
- Refreshing stale titles

## Technical Details

### Thread Safety

All title fetching happens in background threads:
- UI never freezes
- Multiple fetches can run in parallel
- Updates are applied on the main thread (thread-safe)

### Network Behavior

**Fetch Process:**
```python
1. Add protocol if missing (https://)
2. Send HTTP GET request
   - User-Agent: Mozilla/5.0 (to avoid blocking)
   - Timeout: 5 seconds
   - Follow redirects: Yes
3. Parse HTML with BeautifulSoup
4. Extract <title> tag
5. Fallback to og:title meta tag if needed
6. Clean and format title
   - Remove extra whitespace
   - Limit to 200 characters
```

**Error Handling:**
- Network timeout → No update (keeps original name)
- 404/500 errors → No update
- Parse errors → No update
- **Principle:** Better to keep URL name than fail

### Performance

**Single Link:**
- Best case: ~100-500ms
- Average: ~1-2 seconds
- Worst case: 5 seconds (timeout)

**Batch (10 links):**
- Sequential: ~10-50 seconds
- All fetches run in parallel
- No UI blocking

**Memory:**
- Minimal overhead
- Threads are daemon (auto-cleanup)
- No caching (fetches are one-time)

## Configuration

Currently hard-coded, but easily configurable:

### In `utils/title_fetcher.py`:

```python
# Timeout per request
timeout = 5  # seconds

# Max title length
max_length = 200  # characters

# Minimum name length (shorter = likely needs update)
min_name_length = 3  # characters
```

### Future Configuration Options:

Could add settings dialog:
```
┌─────────────────────────────────────────┐
│ Title Fetching Settings                 │
├─────────────────────────────────────────┤
│ ☑ Auto-fetch titles on add              │
│ ☑ Scan existing links on startup        │
│ ☐ Fetch titles for all new links        │
│   (even with custom names)               │
│                                         │
│ Timeout: [5] seconds                    │
│ Max title length: [200] characters      │
│                                         │
│         [Save]  [Cancel]                │
└─────────────────────────────────────────┘
```

## Examples

### Example 1: Adding Links

**Input:**
```
https://github.com/anthropics/claude-code
https://python.org
https://news.ycombinator.com
```

**Immediate Result (0ms):**
```
Name                                  | URL
--------------------------------------|---------------------------
https://github.com/anthropics/...    | github.com/anthropics/...
https://python.org                   | python.org
https://news.ycombinator.com         | news.ycombinator.com
```

**After Fetching (1-5s):**
```
Name                                  | URL
--------------------------------------|---------------------------
anthropics/claude-code               | github.com/anthropics/...
Welcome to Python.org                | python.org
Hacker News                          | news.ycombinator.com
```

### Example 2: Retroactive Scan

**Before (existing links):**
```
Name                      | URL                      | Action
--------------------------|--------------------------|----------
https://example.com       | https://example.com      | ✓ Fetch
My Important Link         | https://important.com    | ✗ Skip
github.com               | https://github.com       | ✓ Fetch
Work Project             | https://work.com         | ✗ Skip
```

**After Scan:**
```
Name                      | URL                      | Changed
--------------------------|--------------------------|----------
Example Domain           | https://example.com      | ✓ Yes
My Important Link         | https://important.com    | ✗ No
GitHub - Official Site   | https://github.com       | ✓ Yes
Work Project             | https://work.com         | ✗ No
```

### Example 3: Smart Detection Edge Cases

**Test Cases:**

| Original Name | URL | Should Fetch? | Reason |
|--------------|-----|---------------|--------|
| `https://example.com` | `https://example.com` | ✅ Yes | Exact match |
| `example.com` | `https://example.com` | ✅ Yes | URL without protocol |
| `Example Site` | `https://example.com` | ❌ No | Custom name |
| `ex` | `https://example.com` | ✅ Yes | Too short (< 3) |
| `www.example.com` | `https://example.com` | ✅ Yes | Looks like URL |
| `Check out https://example.com` | `https://example.com` | ✅ Yes | Contains URL |
| `My Research Notes` | `https://example.com` | ❌ No | Descriptive name |

## Troubleshooting

### "Titles aren't updating"

**Check:**
1. Is the link name already descriptive?
   - System won't override custom names
2. Is the website blocking requests?
   - Some sites block automated access
3. Network connection?
   - Title fetching requires internet

**Solution:**
- For custom names: This is expected behavior ✓
- For blocked sites: Edit manually
- For network issues: Run manual scan later (Ctrl+Shift+T)

### "Wrong title fetched"

**Cause:**
- Website has misleading `<title>` tag
- Page title is generic ("Home", "Index")

**Solution:**
- Edit the link manually (will never be overwritten)
- System respects manual edits

### "Fetching is slow"

**Expected:**
- First link: 1-2 seconds
- 10 links: 10-20 seconds (parallel)
- 100 links: 1-2 minutes

**Why:**
- Each site has different response time
- 5-second timeout per site
- Network latency varies

**Tips:**
- Continue working (non-blocking)
- Titles update as they arrive
- Check back in a minute

## Privacy & Security

### Network Requests

- **What's sent:** HTTP GET to the URL you pasted
- **User-Agent:** Generic browser string
- **Cookies:** None
- **Headers:** Minimal (just User-Agent)

### Data Storage

- **Titles:** Stored locally in `profiles.json`
- **No tracking:** No analytics or telemetry
- **No cloud:** Everything stays on your device

### Security

- **HTTPS preferred:** Automatically upgrades HTTP → HTTPS
- **Timeout protection:** 5-second limit prevents hanging
- **Error handling:** Failed fetches don't crash app
- **Safe parsing:** BeautifulSoup sanitizes HTML

## Future Enhancements

Potential improvements:

1. **Title History**
   - Track title changes over time
   - Revert to previous titles

2. **Custom Patterns**
   - User-defined rules for when to fetch
   - Per-domain settings

3. **Favicon Fetching**
   - Grab site icons too
   - Visual link identification

4. **Batch Progress**
   - Progress bar for large scans
   - "3/50 titles fetched..."

5. **Caching**
   - Cache fetched titles
   - Avoid re-fetching same URL

6. **Scheduled Scans**
   - Weekly automatic scans
   - Refresh stale titles

7. **Link Validation**
   - Check for 404s
   - Mark broken links

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd+Shift+T` | Manual title scan |

## API Reference

For developers wanting to extend:

```python
from utils.title_fetcher import TitleFetcher

# Fetch a title
title = TitleFetcher.fetch_title("https://example.com")
# Returns: "Example Domain" or None

# Check if should fetch
should = TitleFetcher.should_fetch_title(
    url="https://example.com",
    current_name="https://example.com"
)
# Returns: True

# Get domain name
domain = TitleFetcher.get_domain_name("https://www.example.com")
# Returns: "example.com"
```
