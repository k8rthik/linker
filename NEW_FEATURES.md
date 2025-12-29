# New Features - linker v0.3.0

## 🎯 Feature Summary

This update adds four major features to enhance the linker experience:

### 1. ✨ Undo Delete (Ctrl/Cmd+Z)
- **What it does**: Restores deleted links with a single keystroke
- **How it works**:
  - Maintains a stack of the last 20 delete operations
  - Preserves the original position and all metadata
  - Shows confirmation message with number of restored links
- **Usage**:
  - Delete links as usual (Delete key or Backspace)
  - Press `Ctrl+Z` (or `Cmd+Z` on Mac) to undo the last delete
  - Can undo up to 20 consecutive delete operations

### 2. 🌐 Auto-Fetch Page Titles
- **What it does**: Automatically fetches and uses actual page titles when adding links
- **How it works**:
  - When you add URLs, the app fetches each page in the background
  - Extracts the `<title>` tag or Open Graph title
  - Falls back to domain name if fetching fails
  - Non-blocking - runs in a separate thread
- **Benefits**:
  - No more manual naming of links
  - More descriptive link names automatically
  - Faster workflow when adding multiple links
- **Technical notes**:
  - 5-second timeout per URL
  - Handles redirects automatically
  - Shows "wait" cursor during fetch

### 3. 📊 Link Analytics
- **What it does**: Tracks and displays statistics about your link usage
- **New data tracked**:
  - `open_count`: Number of times each link has been opened
  - Automatically increments when you open a link
- **Analytics Dashboard** (click "Analytics" button):
  - **Current Profile Tab**:
    - Total links, favorites, read/unread counts
    - Total opens and average opens per link
    - Percentages for better insights
  - **All Profiles Tab**:
    - Aggregated statistics across all profiles
    - Total profiles and global link counts
  - **Most Opened Tab**:
    - Top 10 most frequently opened links
    - Ranked list with open counts
- **Data persistence**: Open count is saved with each link

### 4. 🎮 Vim-Style Numeric Prefixes
- **What it does**: Execute commands multiple times with numeric prefixes
- **How it works**:
  - Type a number (e.g., `5`), then press a shortcut
  - The command executes that many times
  - Visual feedback shows the current number in blue brackets `[5]`
  - Press Escape to clear the buffer without executing
- **Supported shortcuts**:
  - `Ctrl/Cmd+D` - Toggle favorite
  - `Ctrl/Cmd+E` - Toggle read/unread
  - `Ctrl/Cmd+R` - Open random link
  - `Ctrl/Cmd+Shift+F` - Open random favorite
  - `Ctrl/Cmd+U` - Open random unread
- **Examples**:
  - `5<Ctrl-R>` - Opens 5 random links
  - `10<Ctrl-D>` - Toggles favorite on the selected link 10 times (back to original state)
  - `3<Ctrl-U>` - Opens 3 random unread links
- **Smart behavior**:
  - Number keys don't interfere with search bar typing
  - Buffer automatically clears after command execution
  - Can't accidentally execute - must press a command key

## 🔧 Technical Changes

### Models
- **Link model** (`models/link.py`):
  - Added `open_count` field (integer, default 0)
  - Updated `mark_as_opened()` to increment count
  - Updated serialization (`to_dict`, `from_dict`) to include `open_count`
  - Backward compatible - existing data automatically gets `open_count=0`

### Services
- No service changes required - uses existing infrastructure

### UI Components
- **New Dialog**: `ui/dialogs/analytics_dialog.py`
  - Tabbed interface for different views
  - Treeview for top links list
  - Calculates statistics dynamically

### Controller
- **New imports**: `threading`, `deque`, `TitleFetcher`, `AnalyticsDialog`
- **New state**:
  - `_undo_stack`: Deque with max 20 entries
  - `_numeric_buffer`: String for vim-style prefix
  - `_numeric_label`: UI widget showing current prefix
- **New methods**:
  - `_on_number_key_pressed()`: Captures numeric input
  - `_update_numeric_display()`: Updates visual feedback
  - `_clear_numeric_buffer()`: Resets numeric input
  - `_get_multiplier()`: Returns integer multiplier
  - `_execute_with_multiplier()`: Wraps command execution
  - `_undo_delete()`: Restores deleted links
  - `_add_fetched_links()`: Callback for async title fetching
  - `_show_analytics()`: Opens analytics dialog
- **Modified methods**:
  - `_add_links()`: Now fetches titles asynchronously
  - `_on_delete_key_pressed()`: Saves to undo stack
  - `_on_escape_pressed()`: Clears numeric buffer first
  - `_setup_keyboard_shortcuts()`: Added number keys and Ctrl+Z

### Utilities
- **New utility**: `utils/title_fetcher.py`
  - `TitleFetcher.fetch_title()`: Fetches page title from URL
  - `TitleFetcher._clean_title()`: Cleans and formats titles
  - `TitleFetcher.get_domain_name()`: Extracts domain for fallback
  - Uses `requests` and `BeautifulSoup4` from requirements.txt

## 📦 Dependencies
All required dependencies were already in `requirements.txt`:
- `requests>=2.28.0` - For HTTP requests
- `beautifulsoup4>=4.11.0` - For HTML parsing
- `lxml>=4.9.0` - For faster parsing

No new dependencies needed!

## 🔄 Data Migration
- Existing `profiles.json` files will work seamlessly
- Links without `open_count` will automatically default to 0
- No manual migration required

## 🎯 Usage Examples

### Undo Delete Workflow
```
1. Select links to delete
2. Press Delete/Backspace
3. Confirm deletion
4. Oops! Made a mistake?
5. Press Ctrl+Z (or Cmd+Z)
6. Links are restored at original positions!
```

### Auto-Fetch Titles Workflow
```
1. Click "Add Links"
2. Paste URLs (one per line):
   https://github.com/anthropics/claude-code
   https://python.org
3. Click OK
4. Watch the cursor change to "wait"
5. Links are added with actual page titles:
   - "Claude Code - GitHub"
   - "Welcome to Python.org"
```

### Analytics Workflow
```
1. Click "Analytics" button
2. View Current Profile stats
3. Switch to "All Profiles" tab for global view
4. Check "Most Opened" to see your favorite links
5. Close dialog
```

### Vim-Style Prefix Workflow
```
1. Type: 5
2. See: [5] appear in blue on the left
3. Press: Ctrl+R
4. Result: 5 random links open!
5. Buffer automatically clears
```

## 🐛 Known Limitations

1. **Title Fetching**:
   - 5-second timeout per URL
   - Requires internet connection
   - Some sites may block automated requests
   - Falls back to domain name on failure

2. **Undo Stack**:
   - Limited to last 20 delete operations
   - Doesn't persist across app restarts
   - Only works for delete operations (not edits)

3. **Analytics**:
   - Open count starts from 0 for existing links
   - Historical data not available
   - Counts browser opens only (not external clicks)

4. **Vim-Style Prefix**:
   - Only works with specific shortcuts
   - Buffer limited to 9999 (4 digits max)
   - No visual indicator for invalid numbers

## 🚀 Future Enhancements

Potential improvements for future versions:
- Redo functionality (Ctrl+Y)
- Undo for other operations (edits, favorites)
- Persistent undo history
- Configurable title fetching options
- More detailed analytics (graphs, trends)
- Export analytics to CSV
- Custom vim-style command mappings
- Macro recording and playback

## 📝 Notes for Developers

- All features follow existing architecture patterns
- No breaking changes to data format
- Backward compatible with v0.2.0 data
- Thread-safe title fetching implementation
- Comprehensive error handling for network operations
