from datetime import datetime
from typing import Optional


class Link:
    """Model representing a link with metadata."""
    
    def __init__(self, name: str, url: str, favorite: bool = False,
                 date_added: Optional[str] = None, last_opened: Optional[str] = None,
                 open_count: int = 0, archived: bool = False):
        self._validate_required_fields(name, url)
        self._name = name.strip()
        self._url = url.strip()
        self._favorite = favorite
        self._date_added = date_added or datetime.now().isoformat()
        self._last_opened = last_opened
        self._open_count = max(0, open_count)  # Ensure non-negative
        self._archived = archived
    
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

    def mark_as_opened(self) -> None:
        """Mark the link as opened with current timestamp and increment open count."""
        self._last_opened = datetime.now().isoformat()
        self._open_count += 1
    
    def toggle_favorite(self) -> None:
        """Toggle the favorite status of the link."""
        self._favorite = not self._favorite
    
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
            "archived": self._archived
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
            archived=data.get("archived", False)
        )
    
    def get_formatted_url(self) -> str:
        """Get URL with proper protocol prefix."""
        if not self._url.startswith(("http://", "https://")):
            return f"https://{self._url}"
        return self._url
    
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