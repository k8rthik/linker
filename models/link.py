from datetime import datetime
from typing import Optional, Set


class Link:
    """Model representing a link with metadata."""
    
    def __init__(self, name: str, url: str, favorite: bool = False, 
                 date_added: Optional[str] = None, last_opened: Optional[str] = None,
                 tags: Optional[Set[str]] = None):
        self._validate_required_fields(name, url)
        self._name = name.strip()
        self._url = url.strip()
        self._favorite = favorite
        self._date_added = date_added or datetime.now().isoformat()
        self._last_opened = last_opened
        self._tags = tags or set()
    
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
    def tags(self) -> Set[str]:
        """Get a copy of the tags set."""
        return self._tags.copy()
    
    @tags.setter
    def tags(self, value: Set[str]) -> None:
        """Set the tags, ensuring they're clean strings."""
        self._tags = {tag.strip() for tag in value if tag.strip()}

    def add_tag(self, tag: str) -> None:
        """Add a tag to the link."""
        if tag and tag.strip():
            self._tags.add(tag.strip())
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the link."""
        self._tags.discard(tag.strip())
    
    def has_tag(self, tag: str) -> bool:
        """Check if link has a specific tag."""
        return tag.strip() in self._tags
    
    def clear_tags(self) -> None:
        """Remove all tags from the link."""
        self._tags.clear()
    
    def get_tags_list(self) -> list:
        """Get tags as a sorted list."""
        return sorted(list(self._tags))

    def mark_as_opened(self) -> None:
        """Mark the link as opened with current timestamp."""
        self._last_opened = datetime.now().isoformat()
    
    def toggle_favorite(self) -> None:
        """Toggle the favorite status of the link."""
        self._favorite = not self._favorite
    
    def is_unread(self) -> bool:
        """Check if the link has never been opened."""
        return self._last_opened is None
    
    def to_dict(self) -> dict:
        """Convert link to dictionary for serialization."""
        return {
            "name": self._name,
            "url": self._url,
            "favorite": self._favorite,
            "date_added": self._date_added,
            "last_opened": self._last_opened,
            "tags": list(self._tags)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Link':
        """Create link from dictionary."""
        tags = data.get("tags", [])
        # Convert from list to set, handling backward compatibility
        if isinstance(tags, list):
            tags_set = set(tags)
        else:
            tags_set = set()
            
        return cls(
            name=data.get("name", ""),
            url=data.get("url", ""),
            favorite=data.get("favorite", False),
            date_added=data.get("date_added"),
            last_opened=data.get("last_opened"),
            tags=tags_set
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
                f"favorite={self._favorite}, date_added='{self._date_added}', "
                f"tags={self._tags})") 