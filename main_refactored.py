#!/usr/bin/env python3
"""
Refactored Link Manager Application

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
"""

import tkinter as tk
from repositories.link_repository import JsonLinkRepository
from services.browser_service import SystemBrowserService
from services.link_service import LinkService
from controllers.link_controller import LinkController


class LinkManagerApp:
    """Main application class that sets up dependency injection."""
    
    def __init__(self):
        self._root = tk.Tk()
        self._setup_dependencies()
        self._setup_window()
        self._create_controller()
    
    def _setup_dependencies(self) -> None:
        """Setup dependency injection container."""
        # Create repository (data layer)
        self._repository = JsonLinkRepository("links.json")
        
        # Create services (business logic layer)
        self._browser_service = SystemBrowserService()
        self._link_service = LinkService(self._repository, self._browser_service)
    
    def _setup_window(self) -> None:
        """Setup main window properties."""
        self._root.title("linker")
        self._root.geometry("800x600")
        self._root.minsize(600, 400)
    
    def _create_controller(self) -> None:
        """Create the main controller (presentation layer)."""
        self._controller = LinkController(self._root, self._link_service)
    
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