#!/usr/bin/env python3
"""
Refactored Link Manager Application with Profiles

This application follows SOLID principles and design patterns:
- Single Responsibility Principle: Each class has one responsibility
- Open/Closed Principle: Easy to extend without modifying existing code
- Liskov Substitution Principle: Interfaces can be substituted
- Interface Segregation Principle: Focused interfaces
- Dependency Inversion Principle: Dependencies are injected

Design Patterns Used:
- Repository Pattern: Data access abstraction
- Observer Pattern: UI updates when data changes
- MVC Pattern: Separation of concerns
- Dependency Injection: Loose coupling

Features:
- Profile Management: Create, switch between, and manage multiple profiles
- Each profile contains its own separate set of links
- Import/Export functionality for data backup and migration
- Automatic migration from legacy links.json format
"""

from __version__ import __version__

import logging
import tkinter as tk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

from controllers.profile_controller import ProfileController
from repositories.profile_repository import JsonProfileRepository
from services.browser_service import SystemBrowserService
from services.cache_service import CacheService
from services.profile_service import ProfileService
from services.scraper_service import ScraperService
from utils.resource_manager import get_cache_directory
from utils.video_downloader import YtDlpDownloader


class LinkManagerApp:
    """Main application class that sets up dependency injection with profile support."""

    def __init__(self):
        self._root = tk.Tk()
        self._setup_dependencies()
        self._setup_window()
        self._create_controller()

    def _setup_dependencies(self) -> None:
        """Setup dependency injection container."""
        # Create repository (data layer) - will auto-migrate from links.json if needed
        self._profile_repository = JsonProfileRepository("profiles.json", "links.json")

        # Create services (business logic layer)
        self._browser_service = SystemBrowserService()

        # Create offline cache service before ProfileService so the latter can
        # route opens through the cache when a local copy exists.
        self._cache_service = CacheService(
            repository=self._profile_repository,
            downloader=YtDlpDownloader(),
            cache_dir=get_cache_directory("videos"),
        )

        self._profile_service = ProfileService(
            self._profile_repository,
            self._browser_service,
            cache_service=self._cache_service,
        )

        # Create scraper service
        self._scraper_service = ScraperService(self._profile_service)

    def _setup_window(self) -> None:
        """Setup main window properties."""
        self._root.title(f"linker v{__version__}")
        self._root.geometry("1450x800")
        self._root.minsize(1200, 600)

    def _create_controller(self) -> None:
        """Create the main controller (presentation layer)."""
        self._controller = ProfileController(
            self._root,
            self._profile_service,
            self._scraper_service,
            self._cache_service,
        )

    def run(self) -> None:
        """Start the application."""
        # Defer the backfill so the window paints before we start scanning
        # profiles and submitting cache jobs. 200ms is enough for the first
        # mainloop tick to render the UI on slower machines.
        self._root.after(200, self._cache_service.enqueue_favorites_backfill)
        self._root.mainloop()


def main() -> None:
    """Main entry point."""
    try:
        app = LinkManagerApp()
        app.run()
    except Exception as e:
        print(f"Application error: {e}")
        raise


if __name__ == "__main__":
    main()

