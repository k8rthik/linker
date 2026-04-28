#!/usr/bin/env python3
"""
Comprehensive unit tests for repository layer.
Tests ProfileRepository and JsonProfileRepository implementations.
"""

import sys
import os
import json
import tempfile
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.link import Link
from models.profile import Profile
from repositories.profile_repository import ProfileRepository, JsonProfileRepository


class TestJsonProfileRepositoryInitialization:
    """Test cases for JsonProfileRepository initialization."""

    def test_initialization_with_existing_profiles_file(self):
        """Test initialization when profiles.json exists."""
        profiles_data = [{
            "name": "Test Profile",
            "links": [],
            "created_at": datetime.now().isoformat(),
            "is_default": True
        }]

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "profiles.json")

            with open(file_path, "w") as f:
                json.dump(profiles_data, f)

            with patch('repositories.profile_repository.get_data_file_path', return_value=file_path):
                repo = JsonProfileRepository(file_path=file_path)
                profiles = repo.find_all()

                assert len(profiles) == 1
                assert profiles[0].name == "Test Profile"

    def test_initialization_without_profiles_creates_default(self):
        """Test initialization without profiles creates default profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "profiles.json")

            with patch('repositories.profile_repository.get_data_file_path', return_value=file_path):
                repo = JsonProfileRepository(file_path=file_path)
                profiles = repo.find_all()

                assert len(profiles) == 1
                assert profiles[0].name == "Default"
                assert profiles[0].is_default is True

    def test_initialization_migrates_from_legacy_links(self):
        """Test initialization migrates from legacy links.json."""
        legacy_data = [
            {"name": "Link 1", "url": "https://example.com", "favorite": False},
            {"name": "Link 2", "url": "https://test.com", "favorite": True}
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_path = os.path.join(tmpdir, "profiles.json")
            legacy_path = os.path.join(tmpdir, "links.json")

            with open(legacy_path, "w") as f:
                json.dump(legacy_data, f)

            def get_path(filename):
                if "profiles" in filename:
                    return profiles_path
                return legacy_path

            with patch('repositories.profile_repository.get_data_file_path', side_effect=get_path):
                repo = JsonProfileRepository(file_path=profiles_path, legacy_links_path=legacy_path)
                profiles = repo.find_all()

                assert len(profiles) == 1
                assert profiles[0].name == "Default"
                assert len(profiles[0].links) == 2

    def test_initialization_handles_corrupted_json(self):
        """Test initialization handles corrupted JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "profiles.json")

            with open(file_path, "w") as f:
                f.write("{ invalid json }")

            with patch('repositories.profile_repository.get_data_file_path', return_value=file_path):
                repo = JsonProfileRepository(file_path=file_path)
                profiles = repo.find_all()

                # Should create default profile on error
                assert len(profiles) == 1
                assert profiles[0].name == "Default"


class TestJsonProfileRepositoryFindOperations:
    """Test cases for find operations."""

    def setup_method(self):
        """Setup test repository with sample data."""
        self.tmpdir = tempfile.mkdtemp()
        self.file_path = os.path.join(self.tmpdir, "profiles.json")

        # Create test profiles
        profiles_data = [
            {
                "name": "Profile 1",
                "links": [{"name": "Link 1", "url": "https://example.com"}],
                "created_at": datetime.now().isoformat(),
                "is_default": True
            },
            {
                "name": "Profile 2",
                "links": [],
                "created_at": datetime.now().isoformat(),
                "is_default": False
            }
        ]

        with open(self.file_path, "w") as f:
            json.dump(profiles_data, f)

        with patch('repositories.profile_repository.get_data_file_path', return_value=self.file_path):
            self.repo = JsonProfileRepository(file_path=self.file_path)

    def teardown_method(self):
        """Cleanup temporary files."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_find_all_returns_all_profiles(self):
        """Test find_all returns all profiles."""
        profiles = self.repo.find_all()
        assert len(profiles) == 2

    def test_find_all_returns_copy(self):
        """Test find_all returns a copy, not original list."""
        profiles1 = self.repo.find_all()
        profiles2 = self.repo.find_all()

        assert profiles1 is not profiles2

    def test_find_by_name_finds_existing_profile(self):
        """Test find_by_name finds existing profile."""
        profile = self.repo.find_by_name("Profile 1")

        assert profile is not None
        assert profile.name == "Profile 1"

    def test_find_by_name_returns_none_for_nonexistent(self):
        """Test find_by_name returns None for non-existent profile."""
        profile = self.repo.find_by_name("Nonexistent")

        assert profile is None

    def test_find_default_profile_returns_default(self):
        """Test find_default_profile returns the default profile."""
        profile = self.repo.find_default_profile()

        assert profile is not None
        assert profile.name == "Profile 1"
        assert profile.is_default is True

    def test_find_default_profile_returns_first_if_no_default(self):
        """Test find_default_profile returns first if no default exists."""
        # Manually set all profiles to non-default
        profiles = self.repo.find_all()
        for profile in profiles:
            profile.is_default = False
        self.repo.save_all(profiles)

        profile = self.repo.find_default_profile()

        assert profile is not None
        assert profile.name == "Profile 1"  # First profile

    def test_find_default_profile_returns_none_for_empty_repository(self):
        """Test find_default_profile returns None when no profiles exist."""
        # Create empty repository
        empty_file = os.path.join(self.tmpdir, "empty.json")
        with open(empty_file, "w") as f:
            json.dump([], f)

        with patch('repositories.profile_repository.get_data_file_path', return_value=empty_file):
            empty_repo = JsonProfileRepository(file_path=empty_file)
            # Empty repo will create default profile, so let's clear it manually
            empty_repo._profiles = []

            profile = empty_repo.find_default_profile()

            assert profile is None


class TestJsonProfileRepositorySaveOperations:
    """Test cases for save operations."""

    def setup_method(self):
        """Setup test repository."""
        self.tmpdir = tempfile.mkdtemp()
        self.file_path = os.path.join(self.tmpdir, "profiles.json")

        with patch('repositories.profile_repository.get_data_file_path', return_value=self.file_path):
            self.repo = JsonProfileRepository(file_path=self.file_path)

    def teardown_method(self):
        """Cleanup temporary files."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_all_persists_profiles(self):
        """Test save_all persists profiles to disk."""
        profiles = [
            Profile("Profile 1", is_default=True),
            Profile("Profile 2", is_default=False)
        ]

        self.repo.save_all(profiles)
        self.repo.flush_pending_writes()

        # Verify saved to disk
        with open(self.file_path, "r") as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["name"] == "Profile 1"
        assert data[1]["name"] == "Profile 2"

    def test_save_all_creates_copy(self):
        """Test save_all creates a copy of the list."""
        profiles = [Profile("Profile 1", is_default=True)]

        self.repo.save_all(profiles)

        # Modify original list
        profiles.append(Profile("Profile 2", is_default=False))

        # Repository should have old version
        saved_profiles = self.repo.find_all()
        assert len(saved_profiles) == 1


class TestJsonProfileRepositoryAddOperation:
    """Test cases for add operation."""

    def setup_method(self):
        """Setup test repository."""
        self.tmpdir = tempfile.mkdtemp()
        self.file_path = os.path.join(self.tmpdir, "profiles.json")

        with patch('repositories.profile_repository.get_data_file_path', return_value=self.file_path):
            self.repo = JsonProfileRepository(file_path=self.file_path)

    def teardown_method(self):
        """Cleanup temporary files."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_add_adds_profile(self):
        """Test add adds a new profile."""
        new_profile = Profile("New Profile", is_default=False)

        self.repo.add(new_profile)

        profiles = self.repo.find_all()
        assert len(profiles) == 2  # Default + new
        assert self.repo.find_by_name("New Profile") is not None

    def test_add_persists_to_disk(self):
        """Test add persists to disk."""
        new_profile = Profile("New Profile", is_default=False)

        self.repo.add(new_profile)
        self.repo.flush_pending_writes()

        # Verify saved to disk
        with open(self.file_path, "r") as f:
            data = json.load(f)

        assert len(data) == 2

    def test_add_default_profile_unsets_other_defaults(self):
        """Test adding default profile unsets other defaults."""
        new_profile = Profile("New Default", is_default=True)

        self.repo.add(new_profile)

        profiles = self.repo.find_all()
        default_profiles = [p for p in profiles if p.is_default]

        assert len(default_profiles) == 1
        assert default_profiles[0].name == "New Default"


class TestJsonProfileRepositoryUpdateOperation:
    """Test cases for update operation."""

    def setup_method(self):
        """Setup test repository."""
        self.tmpdir = tempfile.mkdtemp()
        self.file_path = os.path.join(self.tmpdir, "profiles.json")

        profiles_data = [
            {
                "name": "Profile 1",
                "links": [],
                "created_at": datetime.now().isoformat(),
                "is_default": True
            },
            {
                "name": "Profile 2",
                "links": [],
                "created_at": datetime.now().isoformat(),
                "is_default": False
            }
        ]

        with open(self.file_path, "w") as f:
            json.dump(profiles_data, f)

        with patch('repositories.profile_repository.get_data_file_path', return_value=self.file_path):
            self.repo = JsonProfileRepository(file_path=self.file_path)

    def teardown_method(self):
        """Cleanup temporary files."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_update_updates_existing_profile(self):
        """Test update updates an existing profile."""
        updated_profile = Profile("Profile 1", links=[
            Link("New Link", "https://example.com")
        ], is_default=True)

        result = self.repo.update(updated_profile)

        assert result is True

        profile = self.repo.find_by_name("Profile 1")
        assert len(profile.links) == 1

    def test_update_returns_false_for_nonexistent_profile(self):
        """Test update returns False for non-existent profile."""
        nonexistent = Profile("Nonexistent", is_default=False)

        result = self.repo.update(nonexistent)

        assert result is False

    def test_update_default_profile_unsets_other_defaults(self):
        """Test updating to default unsets other defaults."""
        updated_profile = Profile("Profile 2", is_default=True)

        result = self.repo.update(updated_profile)

        assert result is True

        profiles = self.repo.find_all()
        default_profiles = [p for p in profiles if p.is_default]

        assert len(default_profiles) == 1
        assert default_profiles[0].name == "Profile 2"

    def test_update_persists_to_disk(self):
        """Test update persists to disk."""
        updated_profile = Profile("Profile 1", links=[
            Link("New Link", "https://example.com")
        ], is_default=True)

        self.repo.update(updated_profile)
        self.repo.flush_pending_writes()

        # Verify saved to disk
        with open(self.file_path, "r") as f:
            data = json.load(f)

        profile_data = next(p for p in data if p["name"] == "Profile 1")
        assert len(profile_data["links"]) == 1


class TestJsonProfileRepositoryDeleteOperation:
    """Test cases for delete operation."""

    def setup_method(self):
        """Setup test repository."""
        self.tmpdir = tempfile.mkdtemp()
        self.file_path = os.path.join(self.tmpdir, "profiles.json")

        profiles_data = [
            {
                "name": "Profile 1",
                "links": [],
                "created_at": datetime.now().isoformat(),
                "is_default": True
            },
            {
                "name": "Profile 2",
                "links": [],
                "created_at": datetime.now().isoformat(),
                "is_default": False
            }
        ]

        with open(self.file_path, "w") as f:
            json.dump(profiles_data, f)

        with patch('repositories.profile_repository.get_data_file_path', return_value=self.file_path):
            self.repo = JsonProfileRepository(file_path=self.file_path)

    def teardown_method(self):
        """Cleanup temporary files."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_delete_removes_profile(self):
        """Test delete removes a profile."""
        result = self.repo.delete("Profile 2")

        assert result is True
        assert self.repo.find_by_name("Profile 2") is None
        assert len(self.repo.find_all()) == 1

    def test_delete_returns_false_for_nonexistent_profile(self):
        """Test delete returns False for non-existent profile."""
        result = self.repo.delete("Nonexistent")

        assert result is False

    def test_delete_prevents_deleting_last_profile(self):
        """Test delete prevents deleting the last profile."""
        # Delete one profile
        self.repo.delete("Profile 2")

        # Try to delete the last one
        result = self.repo.delete("Profile 1")

        assert result is False
        assert len(self.repo.find_all()) == 1

    def test_delete_default_profile_makes_another_default(self):
        """Test deleting default profile makes another one default."""
        result = self.repo.delete("Profile 1")

        assert result is True

        profiles = self.repo.find_all()
        assert len(profiles) == 1
        assert profiles[0].is_default is True

    def test_delete_non_default_profile_preserves_default(self):
        """Test deleting non-default profile preserves default."""
        result = self.repo.delete("Profile 2")

        assert result is True

        default_profile = self.repo.find_default_profile()
        assert default_profile.name == "Profile 1"

    def test_delete_persists_to_disk(self):
        """Test delete persists to disk."""
        self.repo.delete("Profile 2")
        self.repo.flush_pending_writes()

        # Verify saved to disk
        with open(self.file_path, "r") as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["name"] == "Profile 1"


class TestJsonProfileRepositoryMigration:
    """Test cases for data migration."""

    def test_migration_populates_missing_domains(self):
        """Test migration populates missing domain fields."""
        profiles_data = [{
            "name": "Test Profile",
            "links": [
                {"name": "Link 1", "url": "https://example.com", "domain": ""},
                {"name": "Link 2", "url": "https://test.com"}
            ],
            "created_at": datetime.now().isoformat(),
            "is_default": True
        }]

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "profiles.json")

            with open(file_path, "w") as f:
                json.dump(profiles_data, f)

            with patch('repositories.profile_repository.get_data_file_path', return_value=file_path):
                repo = JsonProfileRepository(file_path=file_path)

                profiles = repo.find_all()
                assert profiles[0].links[0].domain == "example.com"
                assert profiles[0].links[1].domain == "test.com"

    def test_migration_sets_legacy_source(self):
        """Test migration sets source to 'legacy' for existing links."""
        profiles_data = [{
            "name": "Test Profile",
            "links": [
                {"name": "Link 1", "url": "https://example.com"}
            ],
            "created_at": datetime.now().isoformat(),
            "is_default": True
        }]

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "profiles.json")

            with open(file_path, "w") as f:
                json.dump(profiles_data, f)

            with patch('repositories.profile_repository.get_data_file_path', return_value=file_path):
                repo = JsonProfileRepository(file_path=file_path)

                profiles = repo.find_all()
                assert profiles[0].links[0].source == "legacy"


class TestJsonProfileRepositoryValidation:
    """Test cases for profile validation."""

    def test_ensures_at_least_one_default_profile(self):
        """Test repository ensures at least one default profile."""
        profiles_data = [
            {
                "name": "Profile 1",
                "links": [],
                "created_at": datetime.now().isoformat(),
                "is_default": False
            },
            {
                "name": "Profile 2",
                "links": [],
                "created_at": datetime.now().isoformat(),
                "is_default": False
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "profiles.json")

            with open(file_path, "w") as f:
                json.dump(profiles_data, f)

            with patch('repositories.profile_repository.get_data_file_path', return_value=file_path):
                repo = JsonProfileRepository(file_path=file_path)

                # Should have made first profile default
                profiles = repo.find_all()
                default_profiles = [p for p in profiles if p.is_default]

                assert len(default_profiles) == 1
                assert default_profiles[0].name == "Profile 1"

    def test_ensures_only_one_default_profile(self):
        """Test repository ensures only one default profile."""
        profiles_data = [
            {
                "name": "Profile 1",
                "links": [],
                "created_at": datetime.now().isoformat(),
                "is_default": True
            },
            {
                "name": "Profile 2",
                "links": [],
                "created_at": datetime.now().isoformat(),
                "is_default": True
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "profiles.json")

            with open(file_path, "w") as f:
                json.dump(profiles_data, f)

            with patch('repositories.profile_repository.get_data_file_path', return_value=file_path):
                repo = JsonProfileRepository(file_path=file_path)

                # Should have only one default
                profiles = repo.find_all()
                default_profiles = [p for p in profiles if p.is_default]

                assert len(default_profiles) == 1

    def test_skips_invalid_profiles_during_load(self):
        """Test repository skips invalid profiles during load."""
        profiles_data = [
            {
                "name": "Valid Profile",
                "links": [],
                "created_at": datetime.now().isoformat(),
                "is_default": True
            },
            {
                "name": "",  # Invalid: empty name
                "links": [],
                "created_at": datetime.now().isoformat(),
                "is_default": False
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "profiles.json")

            with open(file_path, "w") as f:
                json.dump(profiles_data, f)

            with patch('repositories.profile_repository.get_data_file_path', return_value=file_path):
                repo = JsonProfileRepository(file_path=file_path)

                profiles = repo.find_all()
                # Should only have 1 valid profile
                assert len(profiles) == 1
                assert profiles[0].name == "Valid Profile"


class TestJsonProfileRepositoryErrorHandling:
    """Test cases for error handling."""

    def test_persist_raises_on_write_error(self):
        """flush_pending_writes() must surface I/O errors instead of swallowing them."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "profiles.json")

            with patch('repositories.profile_repository.get_data_file_path', return_value=file_path):
                repo = JsonProfileRepository(file_path=file_path)
                # Ensure the file exists from the initial default-profile write
                repo.flush_pending_writes()

                # Make the directory read-only so the atomic rename fails
                os.chmod(tmpdir, 0o555)

                try:
                    repo.add(Profile("Test", is_default=False))
                    try:
                        repo.flush_pending_writes()
                        assert False, "Should have raised on write failure"
                    except (RuntimeError, PermissionError, OSError):
                        pass
                finally:
                    os.chmod(tmpdir, 0o755)
