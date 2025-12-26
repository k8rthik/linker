# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

linker is a desktop link manager built with Python and Tkinter. It's a personal productivity tool for organizing, searching, and managing bookmarks and URLs with profile support.

## Essential Commands

### Running the Application
```bash
python main_refactored.py
```

### Development Setup
```bash
# Install minimal dependencies (core functionality)
pip install -r requirements-minimal.txt

# Install development dependencies (testing, linting, formatting)
pip install -r requirements-dev.txt

# Install full dependencies (includes web scraping)
pip install -r requirements.txt
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov

# Run a specific test file
pytest tests/test_link_service.py
```

### Code Quality
```bash
# Type checking
mypy .

# Code formatting
black .

# Import sorting
isort .

# Linting
flake8 .
```

### Building the Application
```bash
# Build macOS app bundle using PyInstaller
python build_app.py

# The app will be created at dist/Linker.app
```

### Release Process
```bash
# Create a new release (creates git tag and tarball)
python release.py

# This will:
# - Validate git status
# - Create git tag from __version__.py
# - Generate release archive
# - Extract release notes from CHANGELOG.md
```

## Architecture

linker follows **clean architecture principles** with clear separation of concerns using SOLID principles and several design patterns.

### Layer Architecture

**Models** (`models/`)
- `link.py`: Link entity with metadata (name, url, favorite, dates)
- `profile.py`: Profile entity that contains collections of links
- Pure data models with validation and business logic methods

**Repositories** (`repositories/`)
- `link_repository.py`: Legacy link data access (deprecated)
- `profile_repository.py`: Profile data access with JSON persistence
- Abstract interfaces with concrete JSON implementations
- Handles automatic migration from legacy `links.json` to `profiles.json`
- Uses Repository Pattern for data abstraction

**Services** (`services/`)
- `profile_service.py`: Profile management business logic
- `link_service.py`: Link operations (search, sort, filter)
- `browser_service.py`: System browser integration
- `import_export_service.py`: Import/export functionality with intelligent merging
- Contains business logic and orchestrates repositories

**Controllers** (`controllers/`)
- `profile_controller.py`: Main controller coordinating UI and services
- Implements Observer Pattern for data change notifications
- Handles user interactions and updates views

**UI Components** (`ui/`)
- `components/`: Reusable UI components
  - `link_list_view.py`: Main link display with sorting and selection
  - `profile_selector.py`: Profile dropdown selector
  - `search_bar.py`: Search input with real-time filtering
- `dialogs/`: Modal dialog windows
  - `add_links_dialog.py`: Batch link addition
  - `edit_dialog.py`: Single link editing
  - `profile_manager_dialog.py`: Profile CRUD operations
  - `import_preview_dialog.py`: Import confirmation with summary

**Utils** (`utils/`)
- `date_formatter.py`: Date formatting utilities
- `resource_manager.py`: Path handling for bundled applications (PyInstaller support)

### Key Design Patterns

1. **Repository Pattern**: Abstracts data access (`ProfileRepository` interface)
2. **Dependency Injection**: Services and repositories are injected through constructors
3. **MVC Pattern**: Clear separation between Models, Views (UI), and Controllers
4. **Observer Pattern**: UI components observe data changes

### Data Flow

1. User interacts with UI components
2. UI triggers controller methods
3. Controller calls service layer methods
4. Service layer uses repositories for data access
5. Service layer applies business logic
6. Repository persists changes to JSON
7. Controller updates UI with new data

### Important Implementation Details

**Profile System**
- Each profile has its own isolated set of links
- Exactly one profile must always be marked as default
- The system automatically migrates from legacy `links.json` format on first run
- Profiles are stored in `profiles.json` in the user's data directory

**Data Storage**
- JSON-based persistence for portability
- `profiles.json`: Main storage file with all profiles and links
- `links.json`: Legacy format (auto-migrated)
- Data files are stored relative to the executable for bundled apps (via `resource_manager.py`)

**Import/Export**
- Exports all profiles and links to a single flat JSON array
- Each exported link includes its source profile name
- Import performs intelligent merging:
  - Creates new profiles automatically if they don't exist
  - Detects duplicate URLs and merges metadata
  - Preserves better names and combines favorite status
  - Maintains all date information

**Keyboard Shortcuts Architecture**
- Vim-style single-key shortcuts (no modifiers needed)
- Context-aware: shortcuts only active when search bar not focused
- Context-aware Escape key (clears numeric buffer, search, or selection)
- Vim-style numeric prefixes for repeating commands
- Shortcuts handled at controller level with focus detection

## Testing Strategy

Tests are located in `tests/` directory. When writing new tests:
- Use pytest as the testing framework
- Mock external dependencies (file I/O, browser calls)
- Test business logic in services independently
- Focus on edge cases (empty profiles, duplicate URLs, invalid data)

## Version Management

Version is defined in `__version__.py` as `__version__`. Update this file when bumping versions. The version is:
- Displayed in the window title
- Used by `release.py` for tagging
- Follows semantic versioning (MAJOR.MINOR.PATCH)

## Recent Features (v0.3.0)

### Undo Delete
- Undo stack maintained in controller (`_undo_stack`)
- Stores last 20 delete operations as (indices, links) tuples
- Ctrl/Cmd+Z restores deleted links at original positions
- Stack is in-memory only (doesn't persist across sessions)

### Auto-Fetch Page Titles
- `utils/title_fetcher.py`: Utility for fetching page titles from URLs
- Uses `requests` and `BeautifulSoup4` to extract `<title>` tags
- Runs asynchronously in background thread to avoid blocking UI
- Falls back to domain name if fetch fails
- 5-second timeout per request

### Link Analytics
- `open_count` field added to Link model (tracks how many times opened)
- Analytics dialog shows stats per profile and globally
- Displays most opened links in ranked list
- All statistics calculated dynamically from link data

### Vim-Style Keyboard Shortcuts
- **Single-key commands** (no Cmd/Ctrl needed):
  - `f` - Toggle favorite
  - `r` - Toggle read/unread
  - `o` - Open random link
  - `O` (Shift+o) - Open random favorite
  - `u` - Open random unread
  - `d` - Delete link(s)
  - `e` - Edit link
  - `a` or `n` - Add new links
  - `p` - Manage profiles
  - `t` - Scan titles
  - `z` - Undo delete
  - `l` - Focus link list
  - `/` - Focus search bar
- **Numeric prefixes** (0-9):
  - Build a numeric buffer for repeating commands
  - Visual feedback via `_numeric_label` widget (shows `[N]`)
  - Example: `5o` opens 5 random links
  - Example: `3f` toggles favorite on 3 links
  - Escape clears buffer without executing
- **Context-aware**:
  - Shortcuts only work when search bar not focused (allows typing)
  - Platform-independent shortcuts (Enter, Tab, Space, Escape, Delete, Arrows)
  - Escape: clears numeric buffer → clears search → clears selection

## Known Limitations

- Desktop-only (no mobile app)
- Local storage only (no cloud sync)
- Tkinter GUI (native but limited styling capabilities)
- Cannot delete the last remaining profile
- Title fetching requires internet connection and may fail for some sites
- Undo stack limited to 20 operations and doesn't persist
