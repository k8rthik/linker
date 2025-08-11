# linker

A simple yet powerful desktop link manager built with Python and Tkinter. Designed as a personal productivity tool to help organize, search, and manage your collection of bookmarks and URLs.

> **Note**: This is a personal utility application created by me for individual use. While functional, I don't have any plans for active maintainenance or development.

## What is linker?

linker is a lightweight desktop application that helps you organize and manage your links more effectively than traditional browser bookmarks. Whether you're a student collecting research materials, a developer saving useful resources, or anyone who accumulates lots of interesting URLs, this tool provides a clean interface to store, search, and access your links.

## Key Features

### Link Management
- **Batch Add**: Add multiple URLs at once by pasting them into a single dialog
- **Quick Edit**: Modify link names, URLs, and metadata with a simple interface
- **Smart Validation**: Automatic URL validation and formatting

### Search & Organization
- **Real-time Search**: Instantly filter links as you type
- **Smart Sorting**: Click any column header to sort by name, URL, date added, or last opened
- **Favorites System**: Mark important links for quick access
- **Read/Unread Tracking**: Keep track of which links you've already visited

### Productivity Features
- **Random Discovery**: Open a random link when you want to rediscover something interesting
- **Bulk Operations**: Select multiple links to open, mark as favorite, or delete in batch
- **Status Management**: Toggle read/unread status to track your progress through lists

### Keyboard-First Design (sort of)
- **Quick Access**: Extensive keyboard shortcuts for power users
- **Seamless Navigation**: Tab between search and list, use arrow keys for selection
- **Context-Aware Actions**: Escape key behavior changes based on current focus

### Import/Export
- **Export All Links**: Consolidate all profiles and links into a single JSON file for backup or transfer
- **Import with Options**: Import links with merge or replace options
- **Profile Selection**: Choose which profiles to import from exported files
- **Data Migration**: Easily transfer your link collection between devices or applications

### Coming Soon
- Tagging functionality
- More keybinds 
- Help Menus
- RSS Feed Support 
- Automatic Scraping

## Installation

### Prerequisites
- Python 3.7 or higher
- No additional system dependencies required (uses built-in Tkinter)

### Setup
1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main_refactored.py
   ```

### Optional Development Setup
For development and testing:
```bash
pip install -r requirements-dev.txt
```

## Usage Guide

### Getting Started
1. **Add Your First Links**: Click "Add Links" and paste URLs (one per line)
2. **Organize**: Edit link names to make them more descriptive
3. **Search**: Use the search bar to quickly find specific links
4. **Mark Favorites**: Use Ctrl/Cmd+D to mark important links

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + F` | Focus search bar |
| `Escape` | Clear search or deselect items |
| `Tab` | Switch between search and list |
| `Enter` | Edit selected link |
| `Space` | Open selected links |
| `Ctrl/Cmd + D` | Toggle favorite status |
| `Ctrl/Cmd + E` | Toggle read/unread status |
| `Ctrl/Cmd + R` | Open random link |
| `Ctrl/Cmd + U` | Open random unread link |
| `Double-click` | Open links in browser |
| `Delete/Backspace` | Delete selected links |

### Import/Export Features

**Exporting Your Links:**
1. Click the "Export Links" button in the main interface
2. Choose a location to save your link file
3. All links from all profiles will be exported to a single JSON array file
4. Each link includes all its attributes (name, URL, favorite status, dates) plus the profile it came from

**Importing Links:**
1. Click the "Import Links" button and select a previously exported JSON file
2. Review the import summary showing total links and profiles
3. Confirm the import with intelligent merging:
   - **New profiles** are created automatically if they don't exist
   - **Duplicate URLs** are detected and intelligently merged
   - **Conflicting metadata** is merged (better names, favorite status, dates)
   - **No data loss** - existing links are enhanced, not overwritten

**Export File Format:**
The export creates a simple JSON array where each link looks like:
```json
[
  {
    "name": "Example Link",
    "url": "https://example.com",
    "favorite": false,
    "date_added": "2024-01-01T12:00:00",
    "last_opened": null,
    "profile": "Work"
  }
]
```

### Tips for Effective Use

**For Students:**
- Use descriptive names for research papers and articles
- Mark important sources as favorites
- Use the read/unread system to track research progress
- Export your research links before major projects for backup

**For Developers:**
- Organize documentation links and tutorials
- Use favorites for frequently referenced resources
- Search by technology keywords in URLs or names
- Export project-specific links to share with team members

**For General Use:**
- Add news articles to read later
- Organize shopping or travel planning links
- Keep track of interesting finds for future reference
- Use export feature to backup your link collection regularly

## Technical Details

### Data Storage
- Links are stored in JSON format for simplicity and portability
- Automatic backup on data changes
- Human-readable format for easy manual inspection or migration

### Cross-Platform
- Works on Windows, macOS, and Linux
- Platform-specific keyboard shortcuts (Cmd on Mac, Ctrl elsewhere)

## Limitations & Future Ideas

### Current Limitations
- Desktop-only (no mobile app)
- Local storage only (no cloud sync)
- JSON-only import/export (no browser bookmark formats yet)

### Potential Enhancements
- Browser extension for easier link capture
- Tag system for better organization
- Import from browser bookmarks (HTML, CSV)
- Export to various formats (CSV, HTML, Markdown)
- Basic analytics on link usage
- Cloud sync capabilities

## Contributing

While this is primarily a personal project, suggestions and bug reports are welcome. Since this is a learning project, the focus is on clean, readable code rather than advanced features.

## License

This project is available for personal use and learning. Feel free to adapt it for your own needs.

---

*Created as a personal productivity tool and learning exercise in software architecture. While functional and reliable for personal use, this application is designed primarily for individual productivity rather than enterprise deployment.*
