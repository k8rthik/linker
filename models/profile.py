from datetime import datetime
from typing import List, Optional
from .link import Link


class Profile:
    """Model representing a user profile with its own set of links."""
    
    def __init__(self, name: str, links: Optional[List[Link]] = None, 
                 created_at: Optional[str] = None, is_default: bool = False):
        self._validate_name(name)
        self._name = name.strip()
        self._links = links or []
        self._created_at = created_at or datetime.now().isoformat()
        self._is_default = is_default
    
    @property
    def name(self) -> str:
        return self._name
    
    @name.setter
    def name(self, value: str) -> None:
        self._validate_name(value)
        self._name = value.strip()
    
    @property
    def links(self) -> List[Link]:
        return self._links.copy()
    
    @links.setter
    def links(self, value: List[Link]) -> None:
        self._links = value or []
    
    @property
    def created_at(self) -> str:
        return self._created_at
    
    @property
    def is_default(self) -> bool:
        return self._is_default
    
    @is_default.setter
    def is_default(self, value: bool) -> None:
        self._is_default = value
    
    def add_link(self, link: Link) -> None:
        """Add a link to this profile."""
        self._links.append(link)
    
    def remove_link(self, index: int) -> bool:
        """Remove a link by index. Returns True if successful."""
        if 0 <= index < len(self._links):
            del self._links[index]
            return True
        return False
    
    def update_link(self, index: int, link: Link) -> bool:
        """Update a link by index. Returns True if successful."""
        if 0 <= index < len(self._links):
            self._links[index] = link
            return True
        return False
    
    def get_link_count(self) -> int:
        """Get the number of links in this profile."""
        return len(self._links)
    
    def get_favorite_count(self) -> int:
        """Get the number of favorite links in this profile."""
        return sum(1 for link in self._links if link.favorite)
    
    def to_dict(self) -> dict:
        """Convert profile to dictionary for serialization."""
        return {
            "name": self._name,
            "links": [link.to_dict() for link in self._links],
            "created_at": self._created_at,
            "is_default": self._is_default
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Profile':
        """Create profile from dictionary."""
        links = []
        if "links" in data:
            for link_data in data["links"]:
                try:
                    links.append(Link.from_dict(link_data))
                except (ValueError, KeyError):
                    # Skip invalid links
                    continue
        
        return cls(
            name=data.get("name", ""),
            links=links,
            created_at=data.get("created_at"),
            is_default=data.get("is_default", False)
        )
    
    def _validate_name(self, name: str) -> None:
        """Validate profile name."""
        if not name or not name.strip():
            raise ValueError("Profile name cannot be empty")
        if len(name.strip()) > 50:
            raise ValueError("Profile name cannot exceed 50 characters")
    
    def __str__(self) -> str:
        return f"Profile(name='{self._name}', links={len(self._links)})"
    
    def __repr__(self) -> str:
        return (f"Profile(name='{self._name}', links={len(self._links)}, "
                f"created_at='{self._created_at}', is_default={self._is_default})")