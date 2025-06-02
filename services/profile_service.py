from typing import List, Optional, Callable
from models.profile import Profile
from models.link import Link
from repositories.profile_repository import ProfileRepository
from .browser_service import BrowserService


class ProfileService:
    """Service for managing profiles and their links."""
    
    def __init__(self, profile_repository: ProfileRepository, browser_service: BrowserService):
        self._profile_repository = profile_repository
        self._browser_service = browser_service
        self._current_profile: Optional[Profile] = None
        self._observers: List[Callable[[], None]] = []
        
        # Load current profile
        self._load_current_profile()
    
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
        """Get all links from the current profile."""
        if not self._current_profile:
            return []
        return self._current_profile.links
    
    def add_link(self, link: Link) -> None:
        """Add a link to the current profile."""
        if self._current_profile:
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
    
    def search_links(self, query: str) -> List[Link]:
        """Search links in the current profile."""
        if not self._current_profile or not query:
            return self.get_links()
        
        query_lower = query.lower()
        filtered_links = []
        
        for link in self._current_profile.links:
            if (query_lower in link.name.lower() or 
                query_lower in link.url.lower()):
                filtered_links.append(link)
        
        return filtered_links
    
    def sort_links(self, column: str, reverse: bool = False) -> List[Link]:
        """Sort links in the current profile by specified column."""
        if not self._current_profile:
            return []
        
        links = self._current_profile.links.copy()
        
        if column == "name":
            links.sort(key=lambda x: x.name.lower(), reverse=reverse)
        elif column == "url":
            links.sort(key=lambda x: x.url.lower(), reverse=reverse)
        elif column == "date_added":
            links.sort(key=lambda x: x.date_added, reverse=reverse)
        elif column == "last_opened":
            links.sort(key=lambda x: x.last_opened or "", reverse=reverse)
        elif column == "favorite":
            links.sort(key=lambda x: x.favorite, reverse=reverse)
        
        return links
    
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
        """Notify all observers of changes."""
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