from typing import List, Optional, Callable, Dict, Set
from models.profile import Profile
from models.link import Link
from repositories.profile_repository import ProfileRepository
from .browser_service import BrowserService


class SearchIndex:
    """Fast search index for link collections using inverted indices."""

    def __init__(self):
        self._text_index: Dict[str, Set[int]] = {}  # word -> set of link indices
        self._tag_index: Dict[str, Set[int]] = {}  # tag -> set of link indices
        self._domain_index: Dict[str, Set[int]] = {}  # domain -> set of link indices
        self._indexed_links: List[Link] = []

    def rebuild(self, links: List[Link]) -> None:
        """Rebuild all indices from scratch. O(n * m) where m is avg words per link."""
        self._text_index.clear()
        self._tag_index.clear()
        self._domain_index.clear()
        self._indexed_links = links

        for idx, link in enumerate(links):
            # Index text content (name + URL)
            text_content = f"{link.name} {link.url}".lower()
            words = self._tokenize(text_content)
            for word in words:
                if word not in self._text_index:
                    self._text_index[word] = set()
                self._text_index[word].add(idx)

            # Index tags
            for tag in link.tags:
                tag_lower = tag.lower()
                if tag_lower not in self._tag_index:
                    self._tag_index[tag_lower] = set()
                self._tag_index[tag_lower].add(idx)

            # Index domain
            if link.domain:
                domain_lower = link.domain.lower()
                if domain_lower not in self._domain_index:
                    self._domain_index[domain_lower] = set()
                self._domain_index[domain_lower].add(idx)

    def search(self, query: str, tag_filter: Optional[str] = None,
               domain_filter: Optional[str] = None) -> List[int]:
        """
        Search using indices. Returns list of matching link indices.
        O(k * log n) where k is number of query terms.
        """
        if not query and not tag_filter and not domain_filter:
            return list(range(len(self._indexed_links)))

        result_indices: Optional[Set[int]] = None

        # Text search
        if query:
            query_lower = query.lower()
            words = self._tokenize(query_lower)

            # For each word, get matching indices and intersect
            for word in words:
                word_matches = set()
                # Find all index keys that contain this word (substring match)
                for indexed_word, indices in self._text_index.items():
                    if word in indexed_word:
                        word_matches.update(indices)

                if result_indices is None:
                    result_indices = word_matches
                else:
                    result_indices = result_indices.intersection(word_matches)

                # Early exit if no matches
                if not result_indices:
                    return []

        # Tag filter
        if tag_filter:
            tag_lower = tag_filter.lower()
            tag_matches = self._tag_index.get(tag_lower, set())
            if result_indices is None:
                result_indices = tag_matches
            else:
                result_indices = result_indices.intersection(tag_matches)

        # Domain filter
        if domain_filter:
            domain_lower = domain_filter.lower()
            domain_matches = self._domain_index.get(domain_lower, set())
            if result_indices is None:
                result_indices = domain_matches
            else:
                result_indices = result_indices.intersection(domain_matches)

        return sorted(list(result_indices or set()))

    def get_all_tags(self) -> List[str]:
        """Get all unique tags from the index."""
        return sorted(self._tag_index.keys())

    def get_all_domains(self) -> List[str]:
        """Get all unique domains from the index."""
        return sorted(self._domain_index.keys())

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize text into searchable words."""
        # Split on common delimiters and filter empty strings
        import re
        words = re.split(r'[\s/\-_.:?&=]+', text)
        return [w for w in words if w and len(w) > 1]  # Ignore single-char tokens


class ProfileService:
    """Service for managing profiles and their links."""
    
    def __init__(self, profile_repository: ProfileRepository, browser_service: BrowserService):
        self._profile_repository = profile_repository
        self._browser_service = browser_service
        self._current_profile: Optional[Profile] = None
        self._observers: List[Callable[[], None]] = []
        self._search_index = SearchIndex()

        # Load current profile
        self._load_current_profile()
        self._rebuild_search_index()
    
    def get_all_profiles(self) -> List[Profile]:
        """Get all available profiles."""
        return self._profile_repository.find_all()
    
    def get_current_profile(self) -> Optional[Profile]:
        """Get the currently active profile."""
        return self._current_profile
    
    def switch_to_profile(self, profile_name: str) -> bool:
        """Switch to a different profile."""
        profile = self._profile_repository.find_by_name(profile_name)
        if profile:
            # Save current profile state before switching
            if self._current_profile:
                self._profile_repository.update(self._current_profile)
            
            self._current_profile = profile
            self._notify_observers()
            return True
        return False
    
    def create_profile(self, name: str, make_default: bool = False) -> bool:
        """Create a new profile."""
        try:
            # Check if profile name already exists
            if self._profile_repository.find_by_name(name):
                return False
            
            new_profile = Profile(name, is_default=make_default)
            self._profile_repository.add(new_profile)
            
            # If this is the first profile or made default, switch to it
            if make_default or not self._current_profile:
                self._current_profile = new_profile
                self._notify_observers()
            
            return True
        except ValueError:
            return False
    
    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """Rename an existing profile."""
        try:
            profile = self._profile_repository.find_by_name(old_name)
            if not profile:
                return False
            
            # Check if new name already exists
            if self._profile_repository.find_by_name(new_name):
                return False
            
            profile.name = new_name
            success = self._profile_repository.update(profile)
            
            if success and self._current_profile and self._current_profile.name == old_name:
                self._current_profile = profile
                self._notify_observers()
            
            return success
        except ValueError:
            return False
    
    def delete_profile(self, profile_name: str) -> bool:
        """Delete a profile."""
        # Don't allow deleting current profile if it's the only one
        profiles = self.get_all_profiles()
        if len(profiles) <= 1:
            return False
        
        success = self._profile_repository.delete(profile_name)
        
        if success and self._current_profile and self._current_profile.name == profile_name:
            # Switch to default profile
            default_profile = self._profile_repository.find_default_profile()
            self._current_profile = default_profile
            self._notify_observers()
        
        return success
    
    def set_default_profile(self, profile_name: str) -> bool:
        """Set a profile as the default."""
        profile = self._profile_repository.find_by_name(profile_name)
        if not profile:
            return False
        
        # Remove default status from all profiles
        for p in self.get_all_profiles():
            p.is_default = False
        
        # Set this profile as default
        profile.is_default = True
        return self._profile_repository.update(profile)
    
    # Link management methods for current profile
    def get_links(self) -> List[Link]:
        """Get all non-archived links from the current profile."""
        if not self._current_profile:
            return []
        return self._current_profile.links

    def get_all_links_including_archived(self) -> List[Link]:
        """Get all links from the current profile including archived ones."""
        if not self._current_profile:
            return []
        return self._current_profile.all_links
    
    def add_link(self, link: Link) -> None:
        """Add a link to the current profile."""
        if self._current_profile:
            self._current_profile.add_link(link)
            self._save_current_profile()
            self._notify_observers()

    def add_links_batch(self, links: List[Link]) -> None:
        """Add multiple links to the current profile in a batch (single save, single notification)."""
        if self._current_profile and links:
            for link in links:
                self._current_profile.add_link(link)
            self._save_current_profile()
            self._notify_observers()
    
    def update_link(self, index: int, link: Link) -> bool:
        """Update a link in the current profile."""
        if self._current_profile:
            success = self._current_profile.update_link(index, link)
            if success:
                self._save_current_profile()
                self._notify_observers()
            return success
        return False

    def update_links_batch(self, updates: List[tuple]) -> bool:
        """Update multiple links in a batch (single save, single notification).

        Args:
            updates: List of (index, link) tuples

        Returns:
            True if all updates succeeded, False otherwise
        """
        if not self._current_profile or not updates:
            return False

        all_succeeded = True
        for index, link in updates:
            success = self._current_profile.update_link(index, link)
            if not success:
                all_succeeded = False

        if all_succeeded:
            self._save_current_profile()
            self._notify_observers()

        return all_succeeded
    
    def delete_links(self, indices: List[int]) -> bool:
        """Delete multiple links from the current profile."""
        if not self._current_profile:
            return False
        
        # Sort indices in descending order to avoid index shifting
        for index in sorted(indices, reverse=True):
            self._current_profile.remove_link(index)
        
        self._save_current_profile()
        self._notify_observers()
        return True
    
    def toggle_favorite(self, index: int) -> bool:
        """Toggle favorite status of a link."""
        if self._current_profile:
            links = self._current_profile.links
            if 0 <= index < len(links):
                links[index].toggle_favorite()
                self._save_current_profile()
                self._notify_observers()
                return True
        return False
    
    def open_links(self, indices: List[int]) -> None:
        """Open multiple links in browser."""
        if not self._current_profile:
            return
        
        links = self._current_profile.links
        for index in indices:
            if 0 <= index < len(links):
                link = links[index]
                self._browser_service.open_url(link.get_formatted_url())
                link.mark_as_opened()
        
        self._save_current_profile()
        self._notify_observers()
    
    def search_links(self, query: str, tag_filter: Optional[str] = None,
                     domain_filter: Optional[str] = None) -> List[Link]:
        """Search links using the fast search index."""
        if not self._current_profile:
            return []

        # If no filters, return all links
        if not query and not tag_filter and not domain_filter:
            return self.get_links()

        # Use search index for fast O(log n) search
        matching_indices = self._search_index.search(query, tag_filter, domain_filter)

        # Convert indices to links
        links = self._current_profile.links
        return [links[idx] for idx in matching_indices if idx < len(links)]
    
    def sort_links(self, links: List[Link], column: str, reverse: bool = False) -> List[Link]:
        """Sort links by specified column."""
        if not links:
            return []
        
        sorted_links = links.copy()
        
        if column == "name":
            sorted_links.sort(key=lambda x: x.name.lower(), reverse=reverse)
        elif column == "url":
            sorted_links.sort(key=lambda x: x.url.lower(), reverse=reverse)
        elif column == "date_added":
            sorted_links.sort(key=lambda x: x.date_added, reverse=reverse)
        elif column == "last_opened":
            sorted_links.sort(key=lambda x: x.last_opened or "", reverse=reverse)
        elif column == "favorite":
            sorted_links.sort(key=lambda x: x.favorite, reverse=reverse)
        
        return sorted_links
    
    def get_profile_stats(self, profile_name: Optional[str] = None) -> dict:
        """Get statistics for a profile (current profile if none specified)."""
        profile = self._current_profile
        if profile_name:
            profile = self._profile_repository.find_by_name(profile_name)
        
        if not profile:
            return {"total_links": 0, "favorite_links": 0, "unread_links": 0}
        
        total_links = profile.get_link_count()
        favorite_links = profile.get_favorite_count()
        unread_links = sum(1 for link in profile.links if link.is_unread())
        
        return {
            "total_links": total_links,
            "favorite_links": favorite_links,
            "unread_links": unread_links
        }
    
    # Observer pattern methods
    def add_observer(self, callback: Callable[[], None]) -> None:
        """Add an observer that will be notified when data changes."""
        self._observers.append(callback)
    
    def remove_observer(self, callback: Callable[[], None]) -> None:
        """Remove an observer."""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self) -> None:
        """Notify all observers of changes and rebuild search index."""
        # Rebuild search index before notifying observers (so UI gets fresh index)
        self._rebuild_search_index()

        for callback in self._observers:
            try:
                callback()
            except Exception as e:
                print(f"Error notifying observer: {e}")
    
    def _load_current_profile(self) -> None:
        """Load the default profile as current."""
        self._current_profile = self._profile_repository.find_default_profile()
        if not self._current_profile:
            # Create a default profile if none exists
            self.create_profile("Default", make_default=True)
    
    def _save_current_profile(self) -> None:
        """Save the current profile to repository."""
        if self._current_profile:
            self._profile_repository.update(self._current_profile)

    def _rebuild_search_index(self) -> None:
        """Rebuild the search index with current profile's links."""
        if self._current_profile:
            self._search_index.rebuild(self._current_profile.links)

    def get_all_tags(self) -> List[str]:
        """Get all unique tags from current profile."""
        return self._search_index.get_all_tags()

    def get_all_domains(self) -> List[str]:
        """Get all unique domains from current profile."""
        return self._search_index.get_all_domains()

    def add_tags_to_links(self, indices: List[int], tags: List[str]) -> bool:
        """Add tags to multiple links."""
        if not self._current_profile or not indices or not tags:
            return False

        links = self._current_profile.links
        for index in indices:
            if 0 <= index < len(links):
                for tag in tags:
                    links[index].add_tag(tag)

        self._save_current_profile()
        self._notify_observers()
        return True

    def remove_tags_from_links(self, indices: List[int], tags: List[str]) -> bool:
        """Remove tags from multiple links."""
        if not self._current_profile or not indices or not tags:
            return False

        links = self._current_profile.links
        for index in indices:
            if 0 <= index < len(links):
                for tag in tags:
                    links[index].remove_tag(tag)

        self._save_current_profile()
        self._notify_observers()
        return True