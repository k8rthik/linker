# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2025-11-10

### Fixed
- Fixed keyboard shortcut for opening random favorite links (Cmd+Shift+F on macOS, Ctrl+Shift+F on Windows/Linux) - updated binding to use uppercase F to avoid conflict with search shortcut
- Fixed delete focus behavior when list is sorted - focus now correctly moves down one visual position instead of jumping to unrelated items based on unsorted data order

### Technical Improvements
- Added visual position tracking methods in LinkListView for proper focus management
- Improved delete operation to maintain visual position consistency across different sort orders

## [0.2.0] - 2024-12-19

### Added
- Import/Export functionality for backing up and transferring links
  - Export all links from all profiles to a single JSON file
  - Import links with intelligent merging and duplicate detection
  - Automatic profile creation during import
  - Import preview dialog showing link counts and profiles
- Random favorite link opening functionality
  - New "Open Random Favorite" button in UI
  - Keyboard shortcut support for opening random favorites
- Application version display in window title
- Comprehensive keyboard shortcuts documentation in README

### Fixed
- **Critical Bug**: Fixed link selection issue where first link was incorrectly selected when opening another link
- **Critical Bug**: Fixed arrow navigation to start from currently selected link instead of always defaulting to first link
- Improved focus management in link list view component
- Better selection handling and clearing in UI components
- Enhanced targeted selection management to prevent unwanted selection restoration

### Enhanced
- UI navigation and focus management improvements
- Better keyboard navigation experience
- More robust selection state handling
- Cleaner separation between normal and targeted selection operations

### Technical Improvements
- Added version management system with `__version__.py`
- Improved code organization with better separation of concerns
- Enhanced error handling in selection operations
- Better state management for UI focus operations

## [0.1.0] - 2024-12-18

### Added
- Initial release of linker
- Profile management system
- Link storage and organization
- Search and filtering capabilities
- Keyboard shortcuts for power users
- Random link opening functionality
- Favorite links system
- Read/unread status tracking
- Clean, minimal UI design
- Cross-platform support (Windows, macOS, Linux)

### Features
- **Profile Management**: Create, switch between, and manage multiple profiles
- **Link Organization**: Add, edit, delete, and organize links
- **Search**: Real-time search with instant filtering
- **Sorting**: Click column headers to sort by different criteria
- **Bulk Operations**: Select multiple links for batch operations
- **Keyboard-First Design**: Extensive keyboard shortcuts
- **Status Tracking**: Mark links as read/unread and favorite/unfavorite
- **Random Discovery**: Open random links for rediscovering content

### Technical Foundation
- Built with Python and Tkinter for cross-platform compatibility
- Clean architecture following SOLID principles
- Repository pattern for data access
- Observer pattern for UI updates
- MVC pattern for separation of concerns
- JSON-based data storage for simplicity and portability
