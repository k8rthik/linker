#!/usr/bin/env python3
"""
Example unit tests demonstrating how the refactored architecture enables easy testing.

Run with: python -m pytest tests/ (if you have pytest installed)
Or run directly: python tests/test_link_service.py
"""

import sys
import os
from unittest.mock import Mock, MagicMock
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.link import Link
from repositories.link_repository import LinkRepository
from services.browser_service import BrowserService
from services.link_service import LinkService


class TestLinkService:
    """Test cases for LinkService to demonstrate easy testing with dependency injection."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_repository = Mock(spec=LinkRepository)
        self.mock_browser = Mock(spec=BrowserService)
        self.service = LinkService(self.mock_repository, self.mock_browser)
    
    def test_add_link_calls_repository(self):
        """Test that adding a link calls the repository."""
        # Act
        self.service.add_link("Test Link", "https://example.com")
        
        # Assert
        self.mock_repository.add.assert_called_once()
        args = self.mock_repository.add.call_args[0]
        link = args[0]
        assert isinstance(link, Link)
        assert link.name == "Test Link"
        assert link.url == "https://example.com"
    
    def test_open_link_calls_browser_and_updates_timestamp(self):
        """Test that opening a link calls browser service and updates timestamp."""
        # Arrange
        test_link = Link("Test", "https://example.com")
        self.mock_repository.find_by_id.return_value = test_link
        self.mock_browser.open_url.return_value = True
        
        # Act
        result = self.service.open_link(0)
        
        # Assert
        assert result is True
        self.mock_browser.open_url.assert_called_once_with("https://example.com")
        self.mock_repository.update.assert_called_once()
        # Check that last_opened was set
        updated_link = self.mock_repository.update.call_args[0][1]
        assert updated_link.last_opened is not None
    
    def test_search_links_filters_correctly(self):
        """Test that search functionality works correctly."""
        # Arrange
        links = [
            Link("Python Tutorial", "https://python.org"),
            Link("JavaScript Guide", "https://js.com"),
            Link("Python Advanced", "https://advanced-python.com")
        ]
        self.mock_repository.find_all.return_value = links
        
        # Act
        result = self.service.search_links("python")
        
        # Assert
        assert len(result) == 2
        assert all("python" in link.name.lower() or "python" in link.url.lower() for link in result)
    
    def test_toggle_favorite_updates_link(self):
        """Test that toggling favorite updates the link correctly."""
        # Arrange
        test_link = Link("Test", "https://example.com", favorite=False)
        self.mock_repository.find_by_id.return_value = test_link
        self.mock_repository.update.return_value = True
        
        # Act
        result = self.service.toggle_favorite(0)
        
        # Assert
        assert result is True
        assert test_link.favorite is True
        self.mock_repository.update.assert_called_once_with(0, test_link)
    
    def test_observer_pattern_notifies_observers(self):
        """Test that the observer pattern works correctly."""
        # Arrange
        observer_called = False
        
        def test_observer():
            nonlocal observer_called
            observer_called = True
        
        self.service.add_observer(test_observer)
        
        # Act
        self.service.add_link("Test", "https://example.com")
        
        # Assert
        assert observer_called is True


class TestLink:
    """Test cases for Link model to demonstrate validation."""
    
    def test_link_creation_with_valid_data(self):
        """Test creating a link with valid data."""
        link = Link("Test", "https://example.com")
        assert link.name == "Test"
        assert link.url == "https://example.com"
        assert link.favorite is False
        assert link.last_opened is None
        assert link.date_added is not None
    
    def test_link_validation_rejects_empty_name(self):
        """Test that empty name raises ValueError."""
        try:
            Link("", "https://example.com")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Name is required" in str(e)
    
    def test_link_validation_rejects_empty_url(self):
        """Test that empty URL raises ValueError."""
        try:
            Link("Test", "")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "URL is required" in str(e)
    
    def test_link_get_formatted_url_adds_protocol(self):
        """Test that get_formatted_url adds protocol if missing."""
        link = Link("Test", "example.com")
        assert link.get_formatted_url() == "https://example.com"
        
        link2 = Link("Test", "https://example.com")
        assert link2.get_formatted_url() == "https://example.com"
    
    def test_link_mark_as_opened_sets_timestamp(self):
        """Test that mark_as_opened sets the timestamp."""
        link = Link("Test", "https://example.com")
        assert link.is_unread() is True
        
        link.mark_as_opened()
        assert link.is_unread() is False
        assert link.last_opened is not None


def run_tests():
    """Simple test runner for demonstration."""
    test_classes = [TestLinkService, TestLink]
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\nRunning {test_class.__name__}:")
        print("-" * 40)
        
        # Get test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for test_method_name in test_methods:
            total_tests += 1
            try:
                # Create instance and run setup if it exists
                instance = test_class()
                if hasattr(instance, 'setup_method'):
                    instance.setup_method()
                
                # Run the test method
                test_method = getattr(instance, test_method_name)
                test_method()
                
                print(f"  ✓ {test_method_name}")
                passed_tests += 1
                
            except Exception as e:
                print(f"  ✗ {test_method_name}: {e}")
    
    print(f"\n{passed_tests}/{total_tests} tests passed")
    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 