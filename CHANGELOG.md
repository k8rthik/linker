# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.1] - 2026-05-10

### Fixed
- Multiplied open commands (`10o`, `10O`, `10u`) now sample without replacement, so each invocation opens distinct links instead of re-rolling and reopening the same one
- Unfavoriting a link now cancels any pending offline-cache download and removes the cached file from disk, keeping the cache aligned with the favorites set

## [0.5.0] - 2026-05-09

### Added
- **Offline video cache** for favorited links:
  - Background `yt-dlp` worker auto-downloads videos when a link is favorited
  - Startup backfill enqueues any favorited link that isn't already cached
  - Cache markers and right-click cache actions in the link list
  - Cache management dialog with on-disk size readout, live queue/activity log, and clear-all
  - Opens route to the local cached file when available; cached videos open in QuickTime
- **fyptt.to resolver** that walks the article → iframe → stream chain so `yt-dlp` can download tokenized streams; supports the plain player, `fypttjwstr.php` (JWPlayer + direct mp4), and `fypttjwstrhls.php` (JWPlayer + HLS) variants
- **Archived links** ("soft delete"):
  - Tools menu entry opens an Archived Links dialog with search, restore, and permanent delete
  - Service-layer API for soft-delete, restore, and hard-delete flows
- **Copy links to clipboard**:
  - `c` copies selected URL(s), one per line
  - `C` (Shift+c) copies selected as `Name - URL`
  - `y` copies selected as Markdown links `[Name](URL)`
  - `Cmd/Ctrl+C` and `Cmd/Ctrl+Shift+C` mirror the above on the link list
  - New **Edit** menu, **Copy URLs** button, and right-click "Copy all URLs in view"
- **Background web scraper** with pause/resume, progress bar, and an approval dialog for force-refresh title fetches
- Comprehensive analytics infrastructure with enhanced link metadata tracking
- Help menu with keyboard shortcuts overview

### Changed
- Random-link selection uses a `weighted_choice` helper with a stronger favorite bias and a baseline weight floor for unopened links
- UI theme tokens extracted into `ui/theme.py`
- Build versioning is now derived from `git describe`; app bundle name includes the version

### Fixed
- HLS-sourced video downloads are remuxed into a real ISO MP4 container instead of being left as MPEG-TS with an `.mp4` extension, so QuickTime can play them
- Resolve `yt-dlp` via Homebrew fallback paths when the `.app` bundle is launched from Finder (sanitized PATH)
- Restore page-title autofetch by dropping the dead `auto_named` field
- Preserve list selection across refresh and unblock startup paint
- Default approval dialog checkboxes to deselected
- Repaired pre-existing repository and search-index test failures
- Scraper robots.txt handling and pause behavior; broader URL filtering to skip non-content pages

### Removed
- Dead legacy `LinkController` / `LinkService` / `LinkRepository` layer (superseded by the profile-based architecture)

### Technical Improvements
- Extracted utilities: `utils/date_parser`, `utils/url_parser`, `utils/title_fetcher`, `utils/fyptt_resolver`, `utils/video_downloader`
- Disambiguated `AnalyticsService` method names from `ProfileService`
- Concurrent title fetching with a streaming approval dialog
- Fixed UI freezes caused by background tasks triggering constant refreshes

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
