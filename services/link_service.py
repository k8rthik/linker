import random
from typing import List, Optional, Callable
from models.link import Link
from repositories.link_repository import LinkRepository
from services.browser_service import BrowserService


class LinkService:
    """Service class for link business logic operations."""
    
    def __init__(self, repository: LinkRepository, browser_service: BrowserService):
        self._repository = repository
        self._browser_service = browser_service
        self._observers: List[Callable[[], None]] = []
    
    def add_observer(self, observer: Callable[[], None]) -> None:
        """Add an observer to be notified of changes."""
        self._observers.append(observer)
    
    def remove_observer(self, observer: Callable[[], None]) -> None:
        """Remove an observer."""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def _notify_observers(self) -> None:
        """Notify all observers of changes."""
        for observer in self._observers:
            observer()
    
    def get_all_links(self) -> List[Link]:
        """Get all links."""
        return self._repository.find_all()
    
    def get_link(self, link_id: int) -> Optional[Link]:
        """Get a specific link by ID."""
        return self._repository.find_by_id(link_id)
    
    def add_link(self, name: str, url: str) -> None:
        """Add a new link."""
        link = Link(name=name, url=url)
        self._repository.add(link)
        self._notify_observers()
    
    def add_link_with_tags(self, name: str, url: str, tags: set) -> None:
        """Add a new link with tags."""
        link = Link(name=name, url=url, tags=tags)
        self._repository.add(link)
        self._notify_observers()
    
    def add_links_batch(self, urls: List[str]) -> None:
        """Add multiple links at once."""
        links = self.get_all_links()
        for url in urls:
            if url.strip():
                links.append(Link(name=url.strip(), url=url.strip()))
        self._repository.save_all(links)
        self._notify_observers()
    
    def update_link(self, link_id: int, name: str, url: str, favorite: bool, 
                   date_added: Optional[str] = None, last_opened: Optional[str] = None) -> bool:
        """Update an existing link."""
        try:
            link = Link(name=name, url=url, favorite=favorite, 
                       date_added=date_added, last_opened=last_opened)
            success = self._repository.update(link_id, link)
            if success:
                self._notify_observers()
            return success
        except ValueError:
            return False
    
    def update_link_with_tags(self, link_id: int, name: str, url: str, favorite: bool, 
                             tags: set, date_added: Optional[str] = None, 
                             last_opened: Optional[str] = None) -> bool:
        """Update an existing link with tags."""
        try:
            link = Link(name=name, url=url, favorite=favorite, 
                       date_added=date_added, last_opened=last_opened, tags=tags)
            success = self._repository.update(link_id, link)
            if success:
                self._notify_observers()
            return success
        except ValueError:
            return False
    
    def delete_link(self, link_id: int) -> bool:
        """Delete a link."""
        success = self._repository.delete(link_id)
        if success:
            self._notify_observers()
        return success
    
    def delete_links_batch(self, link_ids: List[int]) -> None:
        """Delete multiple links at once."""
        # Sort in reverse order to avoid index shifting issues
        for link_id in sorted(link_ids, reverse=True):
            self._repository.delete(link_id)
        self._notify_observers()
    
    def toggle_favorite(self, link_id: int) -> bool:
        """Toggle favorite status of a link."""
        link = self._repository.find_by_id(link_id)
        if link:
            link.toggle_favorite()
            success = self._repository.update(link_id, link)
            if success:
                self._notify_observers()
            return success
        return False
    
    def toggle_favorites_batch(self, link_ids: List[int]) -> None:
        """Toggle favorite status for multiple links."""
        for link_id in link_ids:
            link = self._repository.find_by_id(link_id)
            if link:
                link.toggle_favorite()
                self._repository.update(link_id, link)
        self._notify_observers()
    
    def toggle_read_status(self, link_ids: List[int]) -> None:
        """Toggle read status for multiple links."""
        links = [self._repository.find_by_id(link_id) for link_id in link_ids]
        valid_links = [link for link in links if link is not None]
        
        if not valid_links:
            return
        
        # Check if all selected items are unread
        all_unread = all(link.is_unread() for link in valid_links)
        
        for i, link_id in enumerate(link_ids):
            link = valid_links[i] if i < len(valid_links) else None
            if link:
                if all_unread:
                    link.mark_as_opened()
                else:
                    link.last_opened = None
                self._repository.update(link_id, link)
        
        self._notify_observers()
    
    def open_link(self, link_id: int) -> bool:
        """Open a link in browser and mark as opened."""
        link = self._repository.find_by_id(link_id)
        if link:
            success = self._browser_service.open_url(link.get_formatted_url())
            if success:
                link.mark_as_opened()
                self._repository.update(link_id, link)
                self._notify_observers()
            return success
        return False
    
    def open_links_batch(self, link_ids: List[int]) -> None:
        """Open multiple links in browser."""
        for link_id in link_ids:
            link = self._repository.find_by_id(link_id)
            if link:
                success = self._browser_service.open_url(link.get_formatted_url())
                if success:
                    link.mark_as_opened()
                    self._repository.update(link_id, link)
        self._notify_observers()
    
    def open_random_link(self) -> bool:
        """Open a random link."""
        links = self.get_all_links()
        if not links:
            return False
        
        choice = random.choice(links)
        link_id = links.index(choice)
        return self.open_link(link_id)
    
    def open_random_unread_link(self) -> bool:
        """Open a random unread link."""
        links = self.get_all_links()
        unread_links = [link for link in links if link.is_unread()]
        
        if not unread_links:
            return False
        
        choice = random.choice(unread_links)
        link_id = links.index(choice)
        return self.open_link(link_id)
    
    def search_links(self, search_term: str) -> List[Link]:
        """Search links by name and URL."""
        if not search_term.strip():
            return self.get_all_links()
        
        search_term_lower = search_term.lower().strip()
        all_links = self.get_all_links()
        
        return [
            link for link in all_links
            if search_term_lower in link.name.lower() or search_term_lower in link.url.lower()
        ]
    
    def search_links_with_tags(self, search_term: str) -> List[Link]:
        """Search links by name, URL, and tags."""
        if not search_term.strip():
            return self.get_all_links()
        
        search_term_lower = search_term.lower().strip()
        all_links = self.get_all_links()
        
        return [
            link for link in all_links
            if (search_term_lower in link.name.lower() or 
                search_term_lower in link.url.lower() or
                any(search_term_lower in tag.lower() for tag in link.tags))
        ]
    
    def filter_links_by_tag(self, tag: str) -> List[Link]:
        """Filter links that have a specific tag."""
        if not tag.strip():
            return self.get_all_links()
        
        all_links = self.get_all_links()
        return [link for link in all_links if link.has_tag(tag)]
    
    def filter_links_by_tags(self, tags: List[str], match_all: bool = True) -> List[Link]:
        """Filter links by multiple tags.
        
        Args:
            tags: List of tag names to filter by
            match_all: If True, links must have ALL tags. If False, links need ANY tag.
        """
        if not tags:
            return self.get_all_links()
        
        all_links = self.get_all_links()
        
        if match_all:
            return [
                link for link in all_links 
                if all(link.has_tag(tag) for tag in tags)
            ]
        else:
            return [
                link for link in all_links 
                if any(link.has_tag(tag) for tag in tags)
            ]
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags across all links."""
        all_tags = set()
        for link in self.get_all_links():
            all_tags.update(link.tags)
        return sorted(list(all_tags))
    
    def get_tag_usage_count(self) -> dict:
        """Get tag usage count across all links."""
        tag_counts = {}
        for link in self.get_all_links():
            for tag in link.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return tag_counts
    
    def add_tag_to_links(self, link_ids: List[int], tag: str) -> None:
        """Add a tag to multiple links."""
        if not tag.strip():
            return
        
        for link_id in link_ids:
            link = self._repository.find_by_id(link_id)
            if link:
                link.add_tag(tag)
                self._repository.update(link_id, link)
        self._notify_observers()
    
    def remove_tag_from_links(self, link_ids: List[int], tag: str) -> None:
        """Remove a tag from multiple links."""
        if not tag.strip():
            return
        
        for link_id in link_ids:
            link = self._repository.find_by_id(link_id)
            if link:
                link.remove_tag(tag)
                self._repository.update(link_id, link)
        self._notify_observers()
    
    def clear_tags_from_links(self, link_ids: List[int]) -> None:
        """Clear all tags from multiple links."""
        for link_id in link_ids:
            link = self._repository.find_by_id(link_id)
            if link:
                link.clear_tags()
                self._repository.update(link_id, link)
        self._notify_observers()
    
    def sort_links(self, links: List[Link], sort_by: str, reverse: bool = False) -> List[Link]:
        """Sort links by specified criteria."""
        def sort_key(link: Link):
            if sort_by == "favorite":
                return link.favorite
            elif sort_by == "name":
                return link.name.lower()
            elif sort_by == "url":
                return link.url.lower()
            elif sort_by == "date_added":
                return link.date_added
            elif sort_by == "last_opened":
                return link.last_opened or ""
            elif sort_by == "tags":
                return ", ".join(sorted(tag.lower() for tag in link.tags))
            return ""
        
        return sorted(links, key=sort_key, reverse=reverse) 