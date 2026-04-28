import json
import os
import threading
import time
from abc import ABC, abstractmethod
from typing import List, Optional
from models.profile import Profile
from models.link import Link
from utils.resource_manager import get_data_file_path


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
    """JSON file-based implementation of ProfileRepository with optimized persistence."""

    def __init__(self, file_path: str = "profiles.json", legacy_links_path: str = "links.json"):
        # Use resource manager to get proper file paths for bundled apps
        self._file_path = str(get_data_file_path(file_path))
        self._legacy_links_path = str(get_data_file_path(legacy_links_path))
        self._profiles: List[Profile] = []

        # Debouncing and background I/O
        self._write_lock = threading.Lock()
        self._write_timer: Optional[threading.Timer] = None
        self._write_delay_seconds = 0.5  # 500ms debounce
        self._pending_write = False

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

            # Migrate existing data to new analytics fields
            self._migrate_analytics_fields()

            # Ensure at least one profile exists and one is default
            self._ensure_valid_profiles()
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading profiles: {e}")
            self._create_default_profile()

    def _migrate_analytics_fields(self) -> None:
        """Migrate existing links to include new analytics fields with defaults."""
        needs_save = False

        for profile in self._profiles:
            for link in profile.all_links:
                # Auto-populate domain if missing or empty
                if not link.domain or link.domain == "":
                    try:
                        link._domain = link._extract_domain(link.url)
                        needs_save = True
                    except Exception:
                        pass

                # Set source to "legacy" for existing links without a source
                if link.source is None:
                    link._source = "legacy"
                    needs_save = True

        # Save migrated data if any changes were made
        if needs_save:
            self._persist_profiles()
            print("Migrated analytics fields for existing links")

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
        """
        Schedule a debounced write to JSON file.
        Uses 500ms debouncing to batch rapid changes into single write.
        """
        with self._write_lock:
            # Cancel any pending write timer
            if self._write_timer is not None:
                self._write_timer.cancel()

            # Schedule a new write after the debounce delay
            self._write_timer = threading.Timer(
                self._write_delay_seconds,
                self._execute_write
            )
            self._write_timer.daemon = True
            self._write_timer.start()

    def _write_to_disk(self) -> None:
        """Serialize profiles and atomically replace the JSON file. Raises on I/O failure."""
        data = [profile.to_dict() for profile in self._profiles]
        json_content = json.dumps(data, indent=4)

        temp_path = f"{self._file_path}.tmp"
        try:
            with open(temp_path, "w") as f:
                f.write(json_content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self._file_path)
        except (IOError, OSError):
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except OSError:
                pass
            raise

    def _execute_write(self) -> None:
        """Background-thread entry point. Swallows I/O errors so the timer doesn't crash."""
        with self._write_lock:
            self._write_timer = None
            try:
                self._write_to_disk()
            except (IOError, OSError) as e:
                print(f"Warning: Failed to save profiles: {e}")

    def flush_pending_writes(self) -> None:
        """
        Force immediate, synchronous write of any pending changes.
        Raises IOError/OSError if the write fails.
        """
        with self._write_lock:
            if self._write_timer is not None:
                self._write_timer.cancel()
                self._write_timer = None
            self._write_to_disk()