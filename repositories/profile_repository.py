import json
import os
from abc import ABC, abstractmethod
from typing import List, Optional
from models.profile import Profile
from models.link import Link


class ProfileRepository(ABC):
    """Abstract repository interface for profile data access."""
    
    @abstractmethod
    def find_all(self) -> List[Profile]:
        """Retrieve all profiles."""
        pass
    
    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Profile]:
        """Find a profile by name."""
        pass
    
    @abstractmethod
    def find_default_profile(self) -> Optional[Profile]:
        """Find the default profile."""
        pass
    
    @abstractmethod
    def save_all(self, profiles: List[Profile]) -> None:
        """Save all profiles."""
        pass
    
    @abstractmethod
    def add(self, profile: Profile) -> None:
        """Add a new profile."""
        pass
    
    @abstractmethod
    def update(self, profile: Profile) -> bool:
        """Update an existing profile. Returns True if successful."""
        pass
    
    @abstractmethod
    def delete(self, profile_name: str) -> bool:
        """Delete a profile by name. Returns True if successful."""
        pass


class JsonProfileRepository(ProfileRepository):
    """JSON file-based implementation of ProfileRepository."""
    
    def __init__(self, file_path: str = "profiles.json", legacy_links_path: str = "links.json"):
        self._file_path = file_path
        self._legacy_links_path = legacy_links_path
        self._profiles: List[Profile] = []
        self._load_profiles()
    
    def find_all(self) -> List[Profile]:
        """Retrieve all profiles."""
        return self._profiles.copy()
    
    def find_by_name(self, name: str) -> Optional[Profile]:
        """Find a profile by name."""
        for profile in self._profiles:
            if profile.name == name:
                return profile
        return None
    
    def find_default_profile(self) -> Optional[Profile]:
        """Find the default profile."""
        for profile in self._profiles:
            if profile.is_default:
                return profile
        # If no default profile, return the first one
        return self._profiles[0] if self._profiles else None
    
    def save_all(self, profiles: List[Profile]) -> None:
        """Save all profiles."""
        self._profiles = profiles.copy()
        self._persist_profiles()
    
    def add(self, profile: Profile) -> None:
        """Add a new profile."""
        # Ensure only one default profile exists
        if profile.is_default:
            for existing_profile in self._profiles:
                existing_profile.is_default = False
        
        self._profiles.append(profile)
        self._persist_profiles()
    
    def update(self, profile: Profile) -> bool:
        """Update an existing profile. Returns True if successful."""
        for i, existing_profile in enumerate(self._profiles):
            if existing_profile.name == profile.name:
                # Ensure only one default profile exists
                if profile.is_default:
                    for other_profile in self._profiles:
                        if other_profile != existing_profile:
                            other_profile.is_default = False
                
                self._profiles[i] = profile
                self._persist_profiles()
                return True
        return False
    
    def delete(self, profile_name: str) -> bool:
        """Delete a profile by name. Returns True if successful."""
        for i, profile in enumerate(self._profiles):
            if profile.name == profile_name:
                # Don't allow deleting the last profile
                if len(self._profiles) <= 1:
                    return False
                
                # If deleting the default profile, make another one default
                was_default = profile.is_default
                del self._profiles[i]
                
                if was_default and self._profiles:
                    self._profiles[0].is_default = True
                
                self._persist_profiles()
                return True
        return False
    
    def _load_profiles(self) -> None:
        """Load profiles from JSON file."""
        # First check if profiles file exists
        if os.path.exists(self._file_path):
            self._load_from_profiles_file()
        else:
            # Migration: Load from legacy links.json if it exists
            self._migrate_from_legacy_links()
    
    def _load_from_profiles_file(self) -> None:
        """Load profiles from the profiles.json file."""
        try:
            with open(self._file_path, "r") as f:
                data = json.load(f)
            
            self._profiles = []
            for profile_data in data:
                try:
                    profile = Profile.from_dict(profile_data)
                    self._profiles.append(profile)
                except (ValueError, KeyError) as e:
                    print(f"Warning: Skipping invalid profile: {e}")
            
            # Ensure at least one profile exists and one is default
            self._ensure_valid_profiles()
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading profiles: {e}")
            self._create_default_profile()
    
    def _migrate_from_legacy_links(self) -> None:
        """Migrate from legacy links.json to profiles system."""
        if os.path.exists(self._legacy_links_path):
            try:
                with open(self._legacy_links_path, "r") as f:
                    links_data = json.load(f)
                
                # Create default profile with existing links
                links = []
                for link_data in links_data:
                    try:
                        # Handle backward compatibility
                        if "date_added" not in link_data:
                            link_data["date_added"] = None
                        if "last_opened" not in link_data:
                            link_data["last_opened"] = None
                        
                        link = Link.from_dict(link_data)
                        links.append(link)
                    except (ValueError, KeyError):
                        continue
                
                default_profile = Profile("Default", links=links, is_default=True)
                self._profiles = [default_profile]
                
                # Save to new format
                self._persist_profiles()
                print("Successfully migrated links to profiles system")
            
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error migrating from legacy links: {e}")
                self._create_default_profile()
        else:
            self._create_default_profile()
    
    def _create_default_profile(self) -> None:
        """Create a default empty profile."""
        default_profile = Profile("Default", is_default=True)
        self._profiles = [default_profile]
        self._persist_profiles()
    
    def _ensure_valid_profiles(self) -> None:
        """Ensure at least one profile exists and exactly one is default."""
        if not self._profiles:
            self._create_default_profile()
            return
        
        # Ensure exactly one default profile
        default_profiles = [p for p in self._profiles if p.is_default]
        
        if not default_profiles:
            # Make the first profile default
            self._profiles[0].is_default = True
        elif len(default_profiles) > 1:
            # Make only the first default profile remain default
            for i, profile in enumerate(self._profiles):
                profile.is_default = (i == 0 and profile.is_default)
    
    def _persist_profiles(self) -> None:
        """Save profiles to JSON file."""
        try:
            data = [profile.to_dict() for profile in self._profiles]
            with open(self._file_path, "w") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            raise RuntimeError(f"Failed to save profiles: {e}")