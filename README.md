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

## Technical Details

### Data Storage
- Links are stored in JSON format for simplicity and portability
- Automatic backup on data changes
- Human-readable format for easy manual inspection or migration

### Cross-Platform
- Works on Windows, macOS, and Linux
- Platform-specific keyboard shortcuts (Cmd on Mac, Ctrl elsewhere)

## Potential Enhancements
- Browser extension for easier link capture
- Import from browser bookmarks
- Export to various formats
- Basic analytics on link usage
