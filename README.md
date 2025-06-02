# linker

A simple yet powerful desktop link manager built with Python and Tkinter. Designed as a personal productivity tool to help organize, search, and manage your collection of bookmarks and URLs.

> **Note**: This is a personal utility application created by me for individual use. While functional and well-structured, it's designed primarily for personal productivity rather than enterprise deployment.

## What is linker?

linker is a lightweight desktop application that helps you organize and manage your links more effectively than traditional browser bookmarks. Whether you're a student collecting research materials, a developer saving useful resources, or anyone who accumulates lots of interesting URLs, this tool provides a clean interface to store, search, and access your links.

## Key Features

### 📝 **Easy Link Management**
- **Batch Add**: Add multiple URLs at once by pasting them into a single dialog
- **Quick Edit**: Modify link names, URLs, and metadata with a simple interface
- **Smart Validation**: Automatic URL validation and formatting

### 🔍 **Powerful Search & Organization**
- **Real-time Search**: Instantly filter links as you type
- **Smart Sorting**: Click any column header to sort by name, URL, date added, or last opened
- **Favorites System**: Mark important links for quick access
- **Read/Unread Tracking**: Keep track of which links you've already visited

### 🎯 **Productivity Features**
- **Random Discovery**: Open a random link when you want to rediscover something interesting
- **Bulk Operations**: Select multiple links to open, mark as favorite, or delete in batch
- **Status Management**: Toggle read/unread status to track your progress through lists

### ⌨️ **Keyboard-First Design**
- **Quick Access**: Extensive keyboard shortcuts for power users
- **Seamless Navigation**: Tab between search and list, use arrow keys for selection
- **Context-Aware Actions**: Escape key behavior changes based on current focus

### Coming Soon
- Tagging functionality
- More keybinds 
- Help Menus
- RSS Feed Support 
- Automatic Scraping

## Screenshots

*The clean, minimal interface focuses on your links without distractions*

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

### Tips for Effective Use

**For Students:**
- Use descriptive names for research papers and articles
- Mark important sources as favorites
- Use the read/unread system to track research progress

**For Developers:**
- Organize documentation links and tutorials
- Use favorites for frequently referenced resources
- Search by technology keywords in URLs or names

**For General Use:**
- Add news articles to read later
- Organize shopping or travel planning links
- Keep track of interesting finds for future reference

## Technical Details

### Architecture
The application follows clean architecture principles with clear separation between data storage, business logic, and user interface. This makes it reliable and easy to maintain.

### Data Storage
- Links are stored in JSON format for simplicity and portability
- Automatic backup on data changes
- Human-readable format for easy manual inspection or migration

### Cross-Platform
- Works on Windows, macOS, and Linux
- Native look and feel on each platform
- Platform-specific keyboard shortcuts (Cmd on Mac, Ctrl elsewhere)

## Limitations & Future Ideas

### Current Limitations
- Desktop-only (no mobile app)
- Local storage only (no cloud sync)
- Basic import/export options

### Potential Enhancements
- Browser extension for easier link capture
- Tag system for better organization
- Import from browser bookmarks
- Export to various formats
- Basic analytics on link usage

## Contributing

While this is primarily a personal project, suggestions and bug reports are welcome. Since this is a learning project, the focus is on clean, readable code rather than advanced features.

## License

This project is available for personal use and learning. Feel free to adapt it for your own needs.

---

*Created as a personal productivity tool and learning exercise in software architecture. While functional and reliable for personal use, this application is designed primarily for individual productivity rather than enterprise deployment.*