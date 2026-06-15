from datetime import datetime
from typing import Optional, List
from utils.date_parser import safe_parse_iso
from utils.url_parser import extract_domain


# Cache status constants for offline video caching.
# A link is considered "openable offline" only when status == CACHE_STATUS_CACHED
# AND cached_path points to an existing file on disk (file existence checked at open time).
CACHE_STATUS_NONE = "none"
CACHE_STATUS_PENDING = "pending"
CACHE_STATUS_DOWNLOADING = "downloading"
CACHE_STATUS_CACHED = "cached"
CACHE_STATUS_FAILED = "failed"

VALID_CACHE_STATUSES = {
    CACHE_STATUS_NONE,
    CACHE_STATUS_PENDING,
    CACHE_STATUS_DOWNLOADING,
    CACHE_STATUS_CACHED,
    CACHE_STATUS_FAILED,
}


class Link:
    """Model representing a link with metadata."""
    
    def __init__(self, name: str, url: str, favorite: bool = False,
                 date_added: Optional[str] = None, last_opened: Optional[str] = None,
                 open_count: int = 0, archived: bool = False,
                 # Usage tracking fields
                 first_opened: Optional[str] = None,
                 favorite_toggle_count: int = 0,
                 last_modified: Optional[str] = None,
                 time_to_first_open: Optional[int] = None,
                 opens_last_30_days: int = 0,
                 # Categorization fields
                 tags: Optional[List[str]] = None,
                 category: Optional[str] = None,
                 domain: str = "",
                 # Metadata fields
                 notes: str = "",
                 source: Optional[str] = None,
                 # Link health fields
                 link_status: str = "unknown",
                 last_checked: Optional[str] = None,
                 http_status_code: Optional[int] = None,
                 # Offline cache fields
                 cache_status: str = CACHE_STATUS_NONE,
                 cached_path: Optional[str] = None,
                 cache_size_bytes: Optional[int] = None,
                 cache_error: Optional[str] = None,
                 # Weighted-random selection
                 points: float = 0.0):
        self._validate_required_fields(name, url)
        self._name = name.strip()
        self._url = url.strip()
        self._favorite = favorite
        self._date_added = date_added or datetime.now().isoformat()
        self._last_opened = last_opened
        self._open_count = max(0, open_count)  # Ensure non-negative
        self._archived = archived

        # Usage tracking
        self._first_opened = first_opened
        self._favorite_toggle_count = max(0, favorite_toggle_count)
        self._last_modified = last_modified
        self._time_to_first_open = time_to_first_open
        self._opens_last_30_days = max(0, opens_last_30_days)

        # Categorization
        self._tags = tags if tags is not None else []
        self._category = category
        self._domain = domain or self._extract_domain(url)

        # Metadata
        self._notes = notes
        self._source = source

        # Link health
        self._link_status = link_status
        self._last_checked = last_checked
        self._http_status_code = http_status_code

        # Offline cache
        if cache_status not in VALID_CACHE_STATUSES:
            raise ValueError(f"Invalid cache_status: {cache_status}")
        self._cache_status = cache_status
        self._cached_path = cached_path
        self._cache_size_bytes = (
            max(0, cache_size_bytes) if cache_size_bytes is not None else None
        )
        self._cache_error = cache_error

        # Selection points. 0.0 is a sentinel meaning "uninitialized" — the
        # service layer assigns the real baseline when a profile is loaded or
        # a link is added.
        self._points = max(0.0, float(points))

    @property
    def name(self) -> str:
        return self._name
    
    @name.setter
    def name(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Name cannot be empty")
        self._name = value.strip()
    
    @property
    def url(self) -> str:
        return self._url
    
    @url.setter
    def url(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("URL cannot be empty")
        self._url = value.strip()
    
    @property
    def favorite(self) -> bool:
        return self._favorite
    
    @favorite.setter
    def favorite(self, value: bool) -> None:
        self._favorite = value
    
    @property
    def date_added(self) -> str:
        return self._date_added
    
    @date_added.setter
    def date_added(self, value: str) -> None:
        self._validate_datetime(value)
        self._date_added = value
    
    @property
    def last_opened(self) -> Optional[str]:
        return self._last_opened
    
    @last_opened.setter
    def last_opened(self, value: Optional[str]) -> None:
        if value is not None:
            self._validate_datetime(value)
        self._last_opened = value

    @property
    def open_count(self) -> int:
        return self._open_count

    @open_count.setter
    def open_count(self, value: int) -> None:
        self._open_count = max(0, value)  # Ensure non-negative

    @property
    def archived(self) -> bool:
        return self._archived

    @archived.setter
    def archived(self, value: bool) -> None:
        self._archived = value

    # Usage tracking properties
    @property
    def first_opened(self) -> Optional[str]:
        return self._first_opened

    @first_opened.setter
    def first_opened(self, value: Optional[str]) -> None:
        if value is not None:
            self._validate_datetime(value)
        self._first_opened = value

    @property
    def favorite_toggle_count(self) -> int:
        return self._favorite_toggle_count

    @favorite_toggle_count.setter
    def favorite_toggle_count(self, value: int) -> None:
        self._favorite_toggle_count = max(0, value)

    @property
    def last_modified(self) -> Optional[str]:
        return self._last_modified

    @last_modified.setter
    def last_modified(self, value: Optional[str]) -> None:
        if value is not None:
            self._validate_datetime(value)
        self._last_modified = value

    @property
    def time_to_first_open(self) -> Optional[int]:
        return self._time_to_first_open

    @time_to_first_open.setter
    def time_to_first_open(self, value: Optional[int]) -> None:
        self._time_to_first_open = value

    @property
    def opens_last_30_days(self) -> int:
        return self._opens_last_30_days

    @opens_last_30_days.setter
    def opens_last_30_days(self, value: int) -> None:
        self._opens_last_30_days = max(0, value)

    # Categorization properties
    @property
    def tags(self) -> List[str]:
        return self._tags

    @tags.setter
    def tags(self, value: List[str]) -> None:
        self._tags = value if value is not None else []

    @property
    def category(self) -> Optional[str]:
        return self._category

    @category.setter
    def category(self, value: Optional[str]) -> None:
        self._category = value

    @property
    def domain(self) -> str:
        return self._domain

    # Metadata properties
    @property
    def notes(self) -> str:
        return self._notes

    @notes.setter
    def notes(self, value: str) -> None:
        self._notes = value

    @property
    def source(self) -> Optional[str]:
        return self._source

    @source.setter
    def source(self, value: Optional[str]) -> None:
        self._source = value

    # Link health properties
    @property
    def link_status(self) -> str:
        return self._link_status

    @link_status.setter
    def link_status(self, value: str) -> None:
        self._link_status = value

    @property
    def last_checked(self) -> Optional[str]:
        return self._last_checked

    @last_checked.setter
    def last_checked(self, value: Optional[str]) -> None:
        if value is not None:
            self._validate_datetime(value)
        self._last_checked = value

    @property
    def http_status_code(self) -> Optional[int]:
        return self._http_status_code

    @http_status_code.setter
    def http_status_code(self, value: Optional[int]) -> None:
        self._http_status_code = value

    # Offline cache properties
    @property
    def cache_status(self) -> str:
        return self._cache_status

    @cache_status.setter
    def cache_status(self, value: str) -> None:
        if value not in VALID_CACHE_STATUSES:
            raise ValueError(f"Invalid cache_status: {value}")
        self._cache_status = value

    @property
    def cached_path(self) -> Optional[str]:
        return self._cached_path

    @cached_path.setter
    def cached_path(self, value: Optional[str]) -> None:
        self._cached_path = value

    @property
    def cache_size_bytes(self) -> Optional[int]:
        return self._cache_size_bytes

    @cache_size_bytes.setter
    def cache_size_bytes(self, value: Optional[int]) -> None:
        self._cache_size_bytes = max(0, value) if value is not None else None

    @property
    def points(self) -> float:
        return self._points

    @points.setter
    def points(self, value: float) -> None:
        self._points = max(0.0, float(value))

    @property
    def cache_error(self) -> Optional[str]:
        return self._cache_error

    @cache_error.setter
    def cache_error(self, value: Optional[str]) -> None:
        self._cache_error = value

    def is_cached(self) -> bool:
        """True iff the link is fully cached and the path is set.
        Caller must still verify the file exists on disk before opening."""
        return (
            self._cache_status == CACHE_STATUS_CACHED
            and self._cached_path is not None
        )

    def mark_cache_pending(self) -> None:
        self._cache_status = CACHE_STATUS_PENDING
        self._cache_error = None

    def mark_cache_downloading(self) -> None:
        self._cache_status = CACHE_STATUS_DOWNLOADING

    def mark_cached(self, path: str, size_bytes: int) -> None:
        self._cache_status = CACHE_STATUS_CACHED
        self._cached_path = path
        self._cache_size_bytes = max(0, size_bytes)
        self._cache_error = None

    def mark_cache_failed(self, error: str) -> None:
        self._cache_status = CACHE_STATUS_FAILED
        self._cache_error = error
        self._cached_path = None
        self._cache_size_bytes = None

    def clear_cache(self) -> None:
        """Reset cache state to none (used after deleting the on-disk file)."""
        self._cache_status = CACHE_STATUS_NONE
        self._cached_path = None
        self._cache_size_bytes = None
        self._cache_error = None

    def mark_as_opened(self) -> None:
        """Mark the link as opened with current timestamp and increment open count."""
        now = datetime.now().isoformat()

        # Set first_opened if this is the first time opening
        if self._first_opened is None:
            self._first_opened = now
            date_added_dt = safe_parse_iso(self._date_added)
            first_opened_dt = safe_parse_iso(self._first_opened)
            if date_added_dt is not None and first_opened_dt is not None:
                self._time_to_first_open = int((first_opened_dt - date_added_dt).total_seconds())
            else:
                self._time_to_first_open = None

        self._last_opened = now
        self._open_count += 1
    
    def toggle_favorite(self) -> None:
        """Toggle the favorite status of the link."""
        self._favorite = not self._favorite
        self._favorite_toggle_count += 1
        self._last_modified = datetime.now().isoformat()
    
    def is_unread(self) -> bool:
        """Check if the link has never been opened."""
        return self._last_opened is None

    def archive(self) -> None:
        """Archive (soft delete) the link."""
        self._archived = True

    def unarchive(self) -> None:
        """Restore an archived link."""
        self._archived = False

    def is_archived(self) -> bool:
        """Check if the link is archived."""
        return self._archived

    def to_dict(self) -> dict:
        """Convert link to dictionary for serialization."""
        return {
            "name": self._name,
            "url": self._url,
            "favorite": self._favorite,
            "date_added": self._date_added,
            "last_opened": self._last_opened,
            "open_count": self._open_count,
            "archived": self._archived,
            # Usage tracking
            "first_opened": self._first_opened,
            "favorite_toggle_count": self._favorite_toggle_count,
            "last_modified": self._last_modified,
            "time_to_first_open": self._time_to_first_open,
            "opens_last_30_days": self._opens_last_30_days,
            # Categorization
            "tags": self._tags,
            "category": self._category,
            "domain": self._domain,
            # Metadata
            "notes": self._notes,
            "source": self._source,
            # Link health
            "link_status": self._link_status,
            "last_checked": self._last_checked,
            "http_status_code": self._http_status_code,
            # Offline cache
            "cache_status": self._cache_status,
            "cached_path": self._cached_path,
            "cache_size_bytes": self._cache_size_bytes,
            "cache_error": self._cache_error,
            # Weighted-random selection
            "points": self._points
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Link':
        """Create link from dictionary."""
        return cls(
            name=data.get("name", ""),
            url=data.get("url", ""),
            favorite=data.get("favorite", False),
            date_added=data.get("date_added"),
            last_opened=data.get("last_opened"),
            open_count=data.get("open_count", 0),
            archived=data.get("archived", False),
            # Usage tracking
            first_opened=data.get("first_opened"),
            favorite_toggle_count=data.get("favorite_toggle_count", 0),
            last_modified=data.get("last_modified"),
            time_to_first_open=data.get("time_to_first_open"),
            opens_last_30_days=data.get("opens_last_30_days", 0),
            # Categorization
            tags=data.get("tags", []),
            category=data.get("category"),
            domain=data.get("domain", ""),
            # Metadata
            notes=data.get("notes", ""),
            source=data.get("source"),
            # Link health
            link_status=data.get("link_status", "unknown"),
            last_checked=data.get("last_checked"),
            http_status_code=data.get("http_status_code"),
            # Offline cache
            cache_status=data.get("cache_status", CACHE_STATUS_NONE),
            cached_path=data.get("cached_path"),
            cache_size_bytes=data.get("cache_size_bytes"),
            cache_error=data.get("cache_error"),
            # Weighted-random selection
            points=data.get("points", 0.0)
        )
    
    def get_formatted_url(self) -> str:
        """Get URL with proper protocol prefix."""
        if not self._url.startswith(("http://", "https://")):
            return f"https://{self._url}"
        return self._url

    # Tag management methods
    def add_tag(self, tag: str) -> None:
        """Add a tag to the link if it doesn't already exist."""
        if tag and tag.strip() and tag not in self._tags:
            self._tags.append(tag.strip())
            self._last_modified = datetime.now().isoformat()

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the link."""
        if tag in self._tags:
            self._tags.remove(tag)
            self._last_modified = datetime.now().isoformat()

    def has_tag(self, tag: str) -> bool:
        """Check if the link has a specific tag."""
        return tag in self._tags

    # Health status method
    def set_health_status(self, status: str, http_code: Optional[int] = None) -> None:
        """Set the health status and HTTP code for the link."""
        self._link_status = status
        self._http_status_code = http_code
        self._last_checked = datetime.now().isoformat()

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        return extract_domain(url)

    def _validate_required_fields(self, name: str, url: str) -> None:
        """Validate that required fields are not empty."""
        if not name or not name.strip():
            raise ValueError("Name is required")
        if not url or not url.strip():
            raise ValueError("URL is required")
    
    def _validate_datetime(self, date_str: str) -> None:
        """Validate datetime string format."""
        try:
            datetime.fromisoformat(date_str)
        except ValueError:
            raise ValueError(f"Invalid datetime format: {date_str}")
    
    def __str__(self) -> str:
        return f"Link(name='{self._name}', url='{self._url}')"
    
    def __repr__(self) -> str:
        return (f"Link(name='{self._name}', url='{self._url}', "
                f"favorite={self._favorite}, date_added='{self._date_added}')") 