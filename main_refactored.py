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
- Automatic migration from legacy links.json format
"""

import tkinter as tk

from controllers.profile_controller import ProfileController
from repositories.profile_repository import JsonProfileRepository
from services.browser_service import SystemBrowserService
from services.profile_service import ProfileService


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
        self._profile_service = ProfileService(
            self._profile_repository, self._browser_service
        )

    def _setup_window(self) -> None:
        """Setup main window properties."""
        self._root.title("linker")
        self._root.geometry("900x700")
        self._root.minsize(700, 500)

    def _create_controller(self) -> None:
        """Create the main controller (presentation layer)."""
        self._controller = ProfileController(self._root, self._profile_service)

    def run(self) -> None:
        """Start the application."""
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

