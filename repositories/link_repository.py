import json
import os
from abc import ABC, abstractmethod
from typing import List, Optional
from models.link import Link


class LinkRepository(ABC):
    """Abstract repository interface for link data access."""
    
    @abstractmethod
    def find_all(self) -> List[Link]:
        """Retrieve all links."""
        pass
    
    @abstractmethod
    def find_by_id(self, link_id: int) -> Optional[Link]:
        """Find a link by its ID (index)."""
        pass
    
    @abstractmethod
    def save_all(self, links: List[Link]) -> None:
        """Save all links."""
        pass
    
    @abstractmethod
    def add(self, link: Link) -> None:
        """Add a new link."""
        pass
    
    @abstractmethod
    def update(self, link_id: int, link: Link) -> bool:
        """Update an existing link. Returns True if successful."""
        pass
    
    @abstractmethod
    def delete(self, link_id: int) -> bool:
        """Delete a link by ID. Returns True if successful."""
        pass


class JsonLinkRepository(LinkRepository):
    """JSON file-based implementation of LinkRepository."""
    
    def __init__(self, file_path: str = "links.json"):
        self._file_path = file_path
        self._links: List[Link] = []
        self._load_links()
    
    def find_all(self) -> List[Link]:
        """Retrieve all links."""
        return self._links.copy()
    
    def find_by_id(self, link_id: int) -> Optional[Link]:
        """Find a link by its ID (index)."""
        if 0 <= link_id < len(self._links):
            return self._links[link_id]
        return None
    
    def save_all(self, links: List[Link]) -> None:
        """Save all links."""
        self._links = links.copy()
        self._persist_links()
    
    def add(self, link: Link) -> None:
        """Add a new link."""
        self._links.append(link)
        self._persist_links()
    
    def update(self, link_id: int, link: Link) -> bool:
        """Update an existing link. Returns True if successful."""
        if 0 <= link_id < len(self._links):
            self._links[link_id] = link
            self._persist_links()
            return True
        return False
    
    def delete(self, link_id: int) -> bool:
        """Delete a link by ID. Returns True if successful."""
        if 0 <= link_id < len(self._links):
            del self._links[link_id]
            self._persist_links()
            return True
        return False
    
    def _load_links(self) -> None:
        """Load links from JSON file."""
        if not os.path.exists(self._file_path):
            self._links = []
            return
        
        try:
            with open(self._file_path, "r") as f:
                data = json.load(f)
            
            self._links = []
            for item in data:
                try:
                    # Handle backward compatibility
                    if "date_added" not in item:
                        item["date_added"] = None
                    if "last_opened" not in item:
                        item["last_opened"] = None
                    
                    link = Link.from_dict(item)
                    self._links.append(link)
                except (ValueError, KeyError) as e:
                    # Skip invalid links but continue loading others
                    print(f"Warning: Skipping invalid link: {e}")
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading links: {e}")
            self._links = []
    
    def _persist_links(self) -> None:
        """Save links to JSON file."""
        try:
            data = [link.to_dict() for link in self._links]
            with open(self._file_path, "w") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            raise RuntimeError(f"Failed to save links: {e}") 