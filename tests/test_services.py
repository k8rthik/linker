#!/usr/bin/env python3
"""
Comprehensive unit tests for service layer.
Tests ProfileService, BrowserService, and other service implementations.
"""

import sys
import os
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.link import Link
from models.profile import Profile
from repositories.profile_repository import ProfileRepository
from services.profile_service import ProfileService
from services.browser_service import BrowserService, SystemBrowserService


class TestProfileServiceInitialization:
    """Test cases for ProfileService initialization."""

    def test_initialization_loads_default_profile(self):
        """Test initialization loads default profile."""
        mock_repo = Mock(spec=ProfileRepository)
        mock_browser = Mock(spec=BrowserService)

        default_profile = Profile("Default", is_default=True)
        mock_repo.find_default_profile.return_value = default_profile

        service = ProfileService(mock_repo, mock_browser)

        assert service.get_current_profile() == default_profile

    def test_initialization_creates_default_if_none_exists(self):
        """Test initialization creates default profile if none exists."""
        mock_repo = Mock(spec=ProfileRepository)
        mock_browser = Mock(spec=BrowserService)

        mock_repo.find_default_profile.return_value = None
        mock_repo.find_by_name.return_value = None

        service = ProfileService(mock_repo, mock_browser)

        # Should have attempted to create a default profile
        mock_repo.add.assert_called_once()


class TestProfileServiceProfileManagement:
    """Test cases for profile management operations."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_repo = Mock(spec=ProfileRepository)
        self.mock_browser = Mock(spec=BrowserService)

        self.default_profile = Profile("Default", is_default=True)
        self.mock_repo.find_default_profile.return_value = self.default_profile

        self.service = ProfileService(self.mock_repo, self.mock_browser)

    def test_get_all_profiles_returns_all_profiles(self):
        """Test get_all_profiles returns all profiles from repository."""
        profiles = [
            Profile("Profile 1", is_default=True),
            Profile("Profile 2", is_default=False)
        ]
        self.mock_repo.find_all.return_value = profiles

        result = self.service.get_all_profiles()

        assert result == profiles

    def test_switch_to_profile_switches_successfully(self):
        """Test switch_to_profile switches to existing profile."""
        new_profile = Profile("New Profile", is_default=False)
        self.mock_repo.find_by_name.return_value = new_profile

        result = self.service.switch_to_profile("New Profile")

        assert result is True
        assert self.service.get_current_profile() == new_profile

    def test_switch_to_profile_saves_current_before_switching(self):
        """Test switch_to_profile saves current profile before switching."""
        new_profile = Profile("New Profile", is_default=False)
        self.mock_repo.find_by_name.return_value = new_profile

        self.service.switch_to_profile("New Profile")

        # Should have saved the default profile
        self.mock_repo.update.assert_called()

    def test_switch_to_profile_returns_false_for_nonexistent(self):
        """Test switch_to_profile returns False for non-existent profile."""
        self.mock_repo.find_by_name.return_value = None

        result = self.service.switch_to_profile("Nonexistent")

        assert result is False

    def test_switch_to_profile_notifies_observers(self):
        """Test switch_to_profile notifies observers."""
        observer_called = False

        def observer():
            nonlocal observer_called
            observer_called = True

        self.service.add_observer(observer)

        new_profile = Profile("New Profile", is_default=False)
        self.mock_repo.find_by_name.return_value = new_profile

        self.service.switch_to_profile("New Profile")

        assert observer_called is True

    def test_create_profile_creates_new_profile(self):
        """Test create_profile creates a new profile."""
        self.mock_repo.find_by_name.return_value = None

        result = self.service.create_profile("New Profile")

        assert result is True
        self.mock_repo.add.assert_called_once()

    def test_create_profile_returns_false_if_name_exists(self):
        """Test create_profile returns False if name already exists."""
        existing_profile = Profile("Existing", is_default=False)
        self.mock_repo.find_by_name.return_value = existing_profile

        result = self.service.create_profile("Existing")

        assert result is False

    def test_create_profile_with_make_default_switches_to_it(self):
        """Test create_profile with make_default switches to new profile."""
        self.mock_repo.find_by_name.return_value = None

        self.service.create_profile("New Profile", make_default=True)

        # Current profile should be updated (in memory)
        current = self.service.get_current_profile()
        assert current.name == "New Profile"

    def test_rename_profile_renames_successfully(self):
        """Test rename_profile renames existing profile."""
        profile = Profile("Old Name", is_default=False)
        self.mock_repo.find_by_name.side_effect = [profile, None]  # First call finds old, second checks new
        self.mock_repo.update.return_value = True

        result = self.service.rename_profile("Old Name", "New Name")

        assert result is True
        assert profile.name == "New Name"

    def test_rename_profile_returns_false_if_old_not_found(self):
        """Test rename_profile returns False if old name not found."""
        self.mock_repo.find_by_name.return_value = None

        result = self.service.rename_profile("Nonexistent", "New Name")

        assert result is False

    def test_rename_profile_returns_false_if_new_name_exists(self):
        """Test rename_profile returns False if new name already exists."""
        old_profile = Profile("Old Name", is_default=False)
        new_profile = Profile("New Name", is_default=False)
        self.mock_repo.find_by_name.side_effect = [old_profile, new_profile]

        result = self.service.rename_profile("Old Name", "New Name")

        assert result is False

    def test_delete_profile_deletes_successfully(self):
        """Test delete_profile deletes profile."""
        self.mock_repo.find_all.return_value = [
            self.default_profile,
            Profile("Profile 2", is_default=False)
        ]
        self.mock_repo.delete.return_value = True

        result = self.service.delete_profile("Profile 2")

        assert result is True

    def test_delete_profile_prevents_deleting_last_profile(self):
        """Test delete_profile prevents deleting the last profile."""
        self.mock_repo.find_all.return_value = [self.default_profile]

        result = self.service.delete_profile("Default")

        assert result is False

    def test_delete_profile_switches_to_default_if_current(self):
        """Test delete_profile switches to default if deleting current."""
        profile2 = Profile("Profile 2", is_default=False)
        self.mock_repo.find_all.return_value = [self.default_profile, profile2]
        self.mock_repo.find_by_name.return_value = profile2

        # Switch to Profile 2
        self.service.switch_to_profile("Profile 2")

        # Delete Profile 2
        self.mock_repo.delete.return_value = True
        self.mock_repo.find_default_profile.return_value = self.default_profile

        self.service.delete_profile("Profile 2")

        # Should have switched back to default
        assert self.service.get_current_profile() == self.default_profile

    def test_set_default_profile_sets_successfully(self):
        """Test set_default_profile sets profile as default."""
        profile2 = Profile("Profile 2", is_default=False)
        self.mock_repo.find_by_name.return_value = profile2
        self.mock_repo.find_all.return_value = [self.default_profile, profile2]
        self.mock_repo.update.return_value = True

        result = self.service.set_default_profile("Profile 2")

        assert result is True
        assert profile2.is_default is True
        assert self.default_profile.is_default is False

    def test_set_default_profile_returns_false_if_not_found(self):
        """Test set_default_profile returns False if profile not found."""
        self.mock_repo.find_by_name.return_value = None

        result = self.service.set_default_profile("Nonexistent")

        assert result is False


class TestProfileServiceLinkManagement:
    """Test cases for link management operations."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_repo = Mock(spec=ProfileRepository)
        self.mock_browser = Mock(spec=BrowserService)

        self.default_profile = Profile("Default", is_default=True)
        self.mock_repo.find_default_profile.return_value = self.default_profile

        self.service = ProfileService(self.mock_repo, self.mock_browser)

    def test_get_links_returns_current_profile_links(self):
        """Test get_links returns links from current profile."""
        link1 = Link("Link 1", "https://example.com")
        link2 = Link("Link 2", "https://test.com")
        self.default_profile.add_link(link1)
        self.default_profile.add_link(link2)

        links = self.service.get_links()

        assert len(links) == 2

    def test_get_links_returns_empty_if_no_current_profile(self):
        """Test get_links returns empty list if no current profile."""
        self.service._current_profile = None

        links = self.service.get_links()

        assert links == []

    def test_add_link_adds_to_current_profile(self):
        """Test add_link adds link to current profile."""
        link = Link("Link 1", "https://example.com")

        self.service.add_link(link)

        assert len(self.default_profile.links) == 1

    def test_add_link_saves_profile(self):
        """Test add_link saves the profile."""
        link = Link("Link 1", "https://example.com")

        self.service.add_link(link)

        self.mock_repo.update.assert_called()

    def test_add_link_notifies_observers(self):
        """Test add_link notifies observers."""
        observer_called = False

        def observer():
            nonlocal observer_called
            observer_called = True

        self.service.add_observer(observer)

        link = Link("Link 1", "https://example.com")
        self.service.add_link(link)

        assert observer_called is True

    def test_add_links_batch_adds_multiple_links(self):
        """Test add_links_batch adds multiple links."""
        links = [
            Link("Link 1", "https://example.com"),
            Link("Link 2", "https://test.com")
        ]

        self.service.add_links_batch(links)

        assert len(self.default_profile.links) == 2

    def test_add_links_batch_single_save_and_notify(self):
        """Test add_links_batch performs single save and notification."""
        observer_count = 0

        def observer():
            nonlocal observer_count
            observer_count += 1

        self.service.add_observer(observer)

        links = [
            Link("Link 1", "https://example.com"),
            Link("Link 2", "https://test.com")
        ]

        self.service.add_links_batch(links)

        # Should have called save and notify only once
        assert self.mock_repo.update.call_count == 1
        assert observer_count == 1

    def test_update_link_updates_successfully(self):
        """Test update_link updates link at index."""
        link1 = Link("Link 1", "https://example.com")
        self.default_profile.add_link(link1)

        updated_link = Link("Updated Link", "https://updated.com")
        result = self.service.update_link(0, updated_link)

        assert result is True

    def test_update_link_returns_false_for_invalid_index(self):
        """Test update_link returns False for invalid index."""
        link = Link("Link 1", "https://example.com")

        result = self.service.update_link(0, link)

        assert result is False

    def test_update_links_batch_updates_multiple_links(self):
        """Test update_links_batch updates multiple links."""
        link1 = Link("Link 1", "https://example.com")
        link2 = Link("Link 2", "https://test.com")
        self.default_profile.add_link(link1)
        self.default_profile.add_link(link2)

        updates = [
            (0, Link("Updated 1", "https://updated1.com")),
            (1, Link("Updated 2", "https://updated2.com"))
        ]

        result = self.service.update_links_batch(updates)

        assert result is True

    def test_delete_links_deletes_multiple_links(self):
        """Test delete_links deletes multiple links."""
        link1 = Link("Link 1", "https://example.com")
        link2 = Link("Link 2", "https://test.com")
        link3 = Link("Link 3", "https://demo.com")
        self.default_profile.add_link(link1)
        self.default_profile.add_link(link2)
        self.default_profile.add_link(link3)

        result = self.service.delete_links([0, 2])

        assert result is True
        assert len(self.default_profile.links) == 1

    def test_toggle_favorite_toggles_successfully(self):
        """Test toggle_favorite toggles favorite status."""
        link = Link("Link 1", "https://example.com", favorite=False)
        self.default_profile.add_link(link)

        result = self.service.toggle_favorite(0)

        assert result is True
        assert link.favorite is True

    def test_toggle_favorite_returns_false_for_invalid_index(self):
        """Test toggle_favorite returns False for invalid index."""
        result = self.service.toggle_favorite(0)

        assert result is False

    def test_open_links_opens_multiple_links(self):
        """Test open_links opens multiple links in browser."""
        link1 = Link("Link 1", "https://example.com")
        link2 = Link("Link 2", "https://test.com")
        self.default_profile.add_link(link1)
        self.default_profile.add_link(link2)

        self.service.open_links([0, 1])

        assert self.mock_browser.open_url.call_count == 2

    def test_open_links_marks_as_opened(self):
        """Test open_links marks links as opened."""
        link = Link("Link 1", "https://example.com")
        self.default_profile.add_link(link)

        self.service.open_links([0])

        assert link.last_opened is not None
        assert link.open_count == 1

    def test_search_links_filters_by_query(self):
        """Test search_links filters links by query."""
        link1 = Link("Python Tutorial", "https://python.org")
        link2 = Link("JavaScript Guide", "https://js.com")
        link3 = Link("Python Advanced", "https://advanced-python.com")
        self.default_profile.add_link(link1)
        self.default_profile.add_link(link2)
        self.default_profile.add_link(link3)

        result = self.service.search_links("python")

        assert len(result) == 2

    def test_search_links_returns_all_if_empty_query(self):
        """Test search_links returns all links if query is empty."""
        link1 = Link("Link 1", "https://example.com")
        link2 = Link("Link 2", "https://test.com")
        self.default_profile.add_link(link1)
        self.default_profile.add_link(link2)

        result = self.service.search_links("")

        assert len(result) == 2

    def test_sort_links_sorts_by_name(self):
        """Test sort_links sorts by name."""
        links = [
            Link("Zebra", "https://z.com"),
            Link("Apple", "https://a.com"),
            Link("Banana", "https://b.com")
        ]

        result = self.service.sort_links(links, "name")

        assert result[0].name == "Apple"
        assert result[1].name == "Banana"
        assert result[2].name == "Zebra"

    def test_sort_links_sorts_by_name_reverse(self):
        """Test sort_links sorts by name in reverse."""
        links = [
            Link("Zebra", "https://z.com"),
            Link("Apple", "https://a.com")
        ]

        result = self.service.sort_links(links, "name", reverse=True)

        assert result[0].name == "Zebra"
        assert result[1].name == "Apple"

    def test_sort_links_sorts_by_favorite(self):
        """Test sort_links sorts by favorite status."""
        links = [
            Link("Link 1", "https://example.com", favorite=False),
            Link("Link 2", "https://test.com", favorite=True)
        ]

        result = self.service.sort_links(links, "favorite")

        assert result[0].favorite is False
        assert result[1].favorite is True


class TestProfileServiceStatistics:
    """Test cases for profile statistics."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_repo = Mock(spec=ProfileRepository)
        self.mock_browser = Mock(spec=BrowserService)

        self.default_profile = Profile("Default", is_default=True)
        self.mock_repo.find_default_profile.return_value = self.default_profile

        self.service = ProfileService(self.mock_repo, self.mock_browser)

    def test_get_profile_stats_returns_stats_for_current_profile(self):
        """Test get_profile_stats returns stats for current profile."""
        link1 = Link("Link 1", "https://example.com", favorite=True)
        link2 = Link("Link 2", "https://test.com", favorite=False)
        link3 = Link("Link 3", "https://demo.com", favorite=True)
        link3.mark_as_opened()  # Mark as read

        self.default_profile.add_link(link1)
        self.default_profile.add_link(link2)
        self.default_profile.add_link(link3)

        stats = self.service.get_profile_stats()

        assert stats["total_links"] == 3
        assert stats["favorite_links"] == 2
        assert stats["unread_links"] == 2

    def test_get_profile_stats_for_specific_profile(self):
        """Test get_profile_stats returns stats for specific profile."""
        other_profile = Profile("Other", is_default=False)
        other_profile.add_link(Link("Link 1", "https://example.com"))

        self.mock_repo.find_by_name.return_value = other_profile

        stats = self.service.get_profile_stats("Other")

        assert stats["total_links"] == 1


class TestProfileServiceObserverPattern:
    """Test cases for observer pattern implementation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_repo = Mock(spec=ProfileRepository)
        self.mock_browser = Mock(spec=BrowserService)

        self.default_profile = Profile("Default", is_default=True)
        self.mock_repo.find_default_profile.return_value = self.default_profile

        self.service = ProfileService(self.mock_repo, self.mock_browser)

    def test_add_observer_registers_observer(self):
        """Test add_observer registers an observer."""
        observer_called = False

        def observer():
            nonlocal observer_called
            observer_called = True

        self.service.add_observer(observer)

        # Trigger notification
        link = Link("Link 1", "https://example.com")
        self.service.add_link(link)

        assert observer_called is True

    def test_remove_observer_unregisters_observer(self):
        """Test remove_observer unregisters an observer."""
        observer_called = False

        def observer():
            nonlocal observer_called
            observer_called = True

        self.service.add_observer(observer)
        self.service.remove_observer(observer)

        # Trigger notification
        link = Link("Link 1", "https://example.com")
        self.service.add_link(link)

        assert observer_called is False

    def test_observer_errors_are_caught(self):
        """Test observer errors are caught and don't break notification."""
        error_observer_called = False
        good_observer_called = False

        def error_observer():
            nonlocal error_observer_called
            error_observer_called = True
            raise Exception("Test error")

        def good_observer():
            nonlocal good_observer_called
            good_observer_called = True

        self.service.add_observer(error_observer)
        self.service.add_observer(good_observer)

        # Trigger notification
        link = Link("Link 1", "https://example.com")
        self.service.add_link(link)

        # Both should be called despite error
        assert error_observer_called is True
        assert good_observer_called is True


class TestSystemBrowserService:
    """Test cases for SystemBrowserService."""

    def test_open_url_formats_url_without_protocol(self):
        """Test open_url adds protocol if missing."""
        service = SystemBrowserService()

        with patch('webbrowser.open_new_tab', return_value=True) as mock_open:
            service.open_url("example.com")

            mock_open.assert_called_once_with("https://example.com")

    def test_open_url_preserves_existing_protocol(self):
        """Test open_url preserves existing protocol."""
        service = SystemBrowserService()

        with patch('webbrowser.open_new_tab', return_value=True) as mock_open:
            service.open_url("http://example.com")

            mock_open.assert_called_once_with("http://example.com")

    def test_open_url_returns_false_for_empty_url(self):
        """Test open_url returns False for empty URL."""
        service = SystemBrowserService()

        result = service.open_url("")

        assert result is False

    def test_open_url_returns_true_on_success(self):
        """Test open_url returns True on successful open."""
        service = SystemBrowserService()

        with patch('webbrowser.open_new_tab', return_value=True):
            result = service.open_url("https://example.com")

            assert result is True

    def test_open_url_falls_back_to_subprocess_on_webbrowser_failure(self):
        """Test open_url falls back to subprocess if webbrowser fails."""
        service = SystemBrowserService()

        with patch('webbrowser.open_new_tab', return_value=False):
            with patch('subprocess.check_call') as mock_subprocess:
                with patch('sys.platform', 'darwin'):
                    result = service.open_url("https://example.com")

                    assert result is True
                    mock_subprocess.assert_called_once()

    def test_open_url_returns_false_on_subprocess_error(self):
        """Test open_url returns False if subprocess also fails."""
        service = SystemBrowserService()

        with patch('webbrowser.open_new_tab', return_value=False):
            with patch('subprocess.check_call', side_effect=Exception("Failed")):
                result = service.open_url("https://example.com")

                assert result is False


class TestProfileServiceArchivedLinks:
    """Tests for archived link operations: soft delete, restore, permanent delete."""

    def setup_method(self):
        self.mock_repo = Mock(spec=ProfileRepository)
        self.mock_browser = Mock(spec=BrowserService)

        self.profile = Profile("Default", is_default=True)
        self.mock_repo.find_default_profile.return_value = self.profile
        self.service = ProfileService(self.mock_repo, self.mock_browser)

    def test_delete_archives_links_rather_than_removing_them(self):
        link = Link("Link 1", "https://example.com")
        self.profile.add_link(link)

        self.service.delete_links([0])

        assert self.service.get_links() == []
        assert len(self.service.get_all_links_including_archived()) == 1
        assert link.is_archived() is True

    def test_get_archived_links_returns_only_archived(self):
        kept = Link("Keep", "https://keep.com")
        gone = Link("Gone", "https://gone.com")
        self.profile.add_link(kept)
        self.profile.add_link(gone)

        self.service.delete_links([1])

        archived = self.profile.get_archived_links()
        assert archived == [gone]

    def test_restore_archived_links_unarchives_and_persists(self):
        link = Link("Link 1", "https://example.com")
        self.profile.add_link(link)
        self.service.delete_links([0])
        self.mock_repo.update.reset_mock()

        restored = self.service.restore_archived_links([link])

        assert restored == 1
        assert link.is_archived() is False
        assert self.service.get_links() == [link]
        self.mock_repo.update.assert_called()

    def test_restore_archived_links_skips_non_archived(self):
        live = Link("Live", "https://live.com")
        self.profile.add_link(live)

        restored = self.service.restore_archived_links([live])

        assert restored == 0

    def test_permanently_delete_links_removes_from_storage(self):
        link = Link("Gone Forever", "https://example.com")
        self.profile.add_link(link)
        self.service.delete_links([0])
        assert len(self.service.get_all_links_including_archived()) == 1

        deleted = self.service.permanently_delete_links([link])

        assert deleted == 1
        assert self.service.get_all_links_including_archived() == []

    def test_permanently_delete_links_returns_zero_for_unknown_links(self):
        ghost = Link("Ghost", "https://ghost.com")

        deleted = self.service.permanently_delete_links([ghost])

        assert deleted == 0


class TestProfileArchiveModel:
    """Unit tests for Profile soft-delete semantics."""

    def test_remove_link_archives_in_place(self):
        profile = Profile("p")
        link = Link("a", "https://a.com")
        profile.add_link(link)

        assert profile.remove_link(0) is True
        assert link.is_archived() is True
        assert profile.links == []
        assert profile.all_links == [link]

    def test_get_archived_links_returns_archived_only(self):
        profile = Profile("p")
        live = Link("live", "https://live.com")
        dead = Link("dead", "https://dead.com")
        profile.add_link(live)
        profile.add_link(dead)
        profile.remove_link(1)

        assert profile.get_archived_links() == [dead]

    def test_permanently_delete_link_removes_from_underlying_list(self):
        profile = Profile("p")
        link = Link("x", "https://x.com")
        profile.add_link(link)
        profile.remove_link(0)

        assert profile.permanently_delete_link(link) is True
        assert profile.all_links == []

    def test_permanently_delete_link_returns_false_for_unknown(self):
        profile = Profile("p")
        stray = Link("stray", "https://stray.com")

        assert profile.permanently_delete_link(stray) is False

