import tkinter as tk
from tkinter import messagebox
from typing import List, Optional, Tuple
from collections import deque
import threading
from datetime import datetime
from models.link import Link
from models.profile import Profile
from services.profile_service import ProfileService
from services.import_export_service import ImportExportService
from services.analytics_service import AnalyticsService
from services.deduplication_service import DeduplicationService
from ui.components.link_list_view import LinkListView
from ui.components.search_bar import SearchBar
from ui.components.profile_selector import ProfileSelector
from ui.dialogs.edit_dialog import EditLinkDialog
from ui.dialogs.add_links_dialog import AddLinksDialog
from ui.dialogs.profile_manager_dialog import ProfileManagerDialog
from ui.dialogs.analytics_dialog import AnalyticsDialog
from ui.dialogs.help_dialog import HelpDialog
from ui.dialogs.scraper_status_dialog import ScraperStatusDialog
from ui.dialogs.archived_links_dialog import ArchivedLinksDialog
from ui.dialogs.deduplication_dialog import (
    DeduplicationPreviewDialog,
    DeduplicationProgressDialog,
    DeduplicationResultsDialog
)
from ui.dialogs.merge_conflict_dialog import MergeConflictDialog
from ui.dialogs.tag_manager_dialog import TagManagerDialog
from ui.dialogs.title_approval_dialog import TitleApprovalDialog
from utils.title_fetcher import TitleFetcher


class ProfileController:
    """Controller for managing profiles and their links with UI interactions."""
    
    def __init__(self, root: tk.Tk, profile_service: ProfileService,
                 scraper_service: Optional['ScraperService'] = None):
        self._root = root
        self._profile_service = profile_service
        self._scraper_service = scraper_service
        self._import_export_service = ImportExportService(profile_service)
        self._deduplication_service = DeduplicationService()
        self._current_search_term = ""
        self._current_sort_column: Optional[str] = None
        self._current_sort_reverse = False
        self._current_filtered_links: List[Link] = []

        # Flag to track when we're performing a targeted selection (e.g., opening random link)
        self._performing_targeted_selection = False

        # Undo stack for delete operations (stores tuples of (indices, links))
        self._undo_stack: deque = deque(maxlen=20)  # Keep last 20 delete operations

        # Vim-style numeric prefix buffer
        self._numeric_buffer = ""
        self._numeric_label: Optional[tk.Label] = None

        # UI components
        self._profile_selector: Optional[ProfileSelector] = None
        self._search_bar: Optional[SearchBar] = None
        self._link_list_view: Optional[LinkListView] = None
        self._scraper_status_dialog: Optional[ScraperStatusDialog] = None
        
        # Register as observer
        self._profile_service.add_observer(self._on_data_changed)

        self._create_ui()
        self._setup_callbacks()
        self._refresh_view()
        # Auto-select first item on initial load
        self._link_list_view.focus(auto_select_first=True)

        # Background scan for title updates (runs after UI is ready)
        self._root.after(1000, self._scan_and_update_titles)  # Wait 1 second after startup

        # Run scraper on startup (5 seconds after startup, after titles start fetching)
        if self._scraper_service:
            self._root.after(5000, self._run_scraper_on_startup)
    
    def _create_ui(self) -> None:
        """Create the user interface."""
        # Menu bar
        self._create_menu_bar()

        # Main container
        container = tk.Frame(self._root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Profile selector at the top
        self._profile_selector = ProfileSelector(container)
        self._profile_selector.pack(fill=tk.X, pady=(0, 10))
        
        # Search bar
        self._search_bar = SearchBar(container)
        
        # Link list view
        list_container = tk.Frame(container)
        list_container.pack(fill=tk.BOTH, expand=True)
        self._link_list_view = LinkListView(list_container)
        
        # Button frame
        self._create_button_frame()
        
        # Setup keyboard shortcuts
        self._setup_keyboard_shortcuts()
    
    def _create_button_frame(self) -> None:
        """Create the button frame with action buttons."""
        btn_frame = tk.Frame(self._root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        # Numeric buffer display (vim-style)
        self._numeric_label = tk.Label(btn_frame, text="", fg="blue", font=("Courier", 10, "bold"))
        self._numeric_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Left side buttons (main actions)
        left_buttons = [
            ("Add Links", self._add_links),
            ("Edit", self._edit_link),
            ("Toggle Favorite", self._toggle_favorite),
            ("Mark Read/Unread", self._toggle_read_status),
            ("Open Random", self._open_random),
            ("Open Random Favorite", self._open_random_favorite),
            ("Open Unread", self._open_random_unread)
        ]
        
        for text, command in left_buttons:
            tk.Button(btn_frame, text=text, command=command).pack(side=tk.LEFT, padx=5)
        
        # Right side buttons (import/export)
        right_frame = tk.Frame(btn_frame)
        right_frame.pack(side=tk.RIGHT)
        
        tk.Button(right_frame, text="Import Links", command=self._import_links).pack(side=tk.LEFT, padx=5)
        tk.Button(right_frame, text="Export Links", command=self._export_links).pack(side=tk.LEFT)

    def _create_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = tk.Menu(self._root)
        self._root.config(menu=menubar)

        # Tags menu
        tags_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tags", menu=tags_menu)
        tags_menu.add_command(label="Add Tags to Selected", command=self._bulk_add_tags)
        tags_menu.add_command(label="Remove Tags from Selected", command=self._bulk_remove_tags)
        tags_menu.add_separator()
        tags_menu.add_command(label="Manage Tags...", command=self._manage_tags)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Find & Merge Duplicates", command=self._deduplicate_links)
        tools_menu.add_separator()
        tools_menu.add_command(label="Scraper Status", command=self._show_scraper_status)
        tools_menu.add_separator()
        tools_menu.add_command(label="Scan Titles", command=self._manual_scan_titles)
        tools_menu.add_command(label="Force Refresh Auto-Named Titles", command=self._force_refresh_titles)
        tools_menu.add_separator()
        tools_menu.add_command(label="View Archived Links", command=self._show_archived_links)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_help)

    def _setup_callbacks(self) -> None:
        """Setup callbacks for UI components."""
        # Profile selector callbacks
        self._profile_selector.set_profile_changed_callback(self._on_profile_changed)
        self._profile_selector.set_manage_profiles_callback(self._on_manage_profiles)
        self._profile_selector.set_analytics_callback(self._show_analytics)
        
        # Search bar callbacks
        self._search_bar.set_search_change_callback(self._on_search_changed)
        self._search_bar.set_clear_callback(self._on_search_cleared)
        self._search_bar.set_open_all_callback(self._on_open_all_clicked)
        self._search_bar.set_filter_change_callback(self._on_filter_changed)
        
        # Link list view callbacks
        self._link_list_view.set_double_click_callback(self._on_links_double_clicked)
        self._link_list_view.set_delete_key_callback(self._on_delete_key_pressed)
        self._link_list_view.set_space_key_callback(self._open_selected)
        self._link_list_view.set_sort_callback(self._on_sort_requested)
    
    def _setup_keyboard_shortcuts(self) -> None:
        """Setup vim-style keyboard shortcuts."""
        self._search_bar.bind_keyboard_shortcuts(self._root)
        self._link_list_view.bind_keyboard_shortcuts(self._root)

        # Escape key handling
        self._root.bind("<Escape>", self._on_escape_pressed)

        # Number keys for vim-style prefix (0-9)
        for num in range(10):
            self._root.bind(str(num), self._on_number_key_pressed)

        # Vim-style single-key shortcuts (only when search bar not focused)
        self._root.bind("f", self._on_vim_key("f", lambda: self._execute_with_multiplier(self._toggle_favorite)))
        self._root.bind("r", self._on_vim_key("r", lambda: self._execute_with_multiplier(self._toggle_read_status)))
        self._root.bind("o", self._on_vim_key("o", lambda: self._execute_with_multiplier(self._open_random)))
        self._root.bind("O", self._on_vim_key("O", lambda: self._execute_with_multiplier(self._open_random_favorite)))
        self._root.bind("u", self._on_vim_key("u", lambda: self._execute_with_multiplier(self._open_random_unread)))
        self._root.bind("d", self._on_vim_key("d", self._delete_selected))
        self._root.bind("e", self._on_vim_key("e", self._edit_link))
        self._root.bind("a", self._on_vim_key("a", self._add_links))
        self._root.bind("n", self._on_vim_key("n", self._add_links))
        self._root.bind("p", self._on_vim_key("p", self._on_manage_profiles))
        self._root.bind("t", self._on_vim_key("t", self._manual_scan_titles))
        self._root.bind("z", self._on_vim_key("z", self._undo_delete))
        self._root.bind("l", self._on_vim_key("l", self._focus_table))
        self._root.bind("/", self._on_vim_key("/", lambda: self._search_bar.focus()))
        self._root.bind("?", self._on_vim_key("?", self._show_help))
        self._root.bind("S", self._on_vim_key("S", self._toggle_scraper_pause))
        self._root.bind("T", self._on_vim_key("T", self._bulk_add_tags))  # Shift+T for bulk add tags
        self._root.bind("R", self._on_vim_key("R", self._force_refresh_titles))  # Shift+R for force refresh titles

        # Platform-independent shortcuts
        self._root.bind("<Return>", lambda e: self._edit_link())
        self._root.bind("<Tab>", self._on_tab_pressed)

    def _on_vim_key(self, key: str, action):
        """
        Create a vim-style key handler that only executes when search bar is not focused.
        Returns a function suitable for bind().
        """
        def handler(event):
            # Don't handle vim keys when search bar has focus (allow typing)
            if self._search_bar.has_focus():
                return

            # Execute the action
            action()
            return "break"  # Prevent default behavior

        return handler

    def _refresh_view(self) -> None:
        """Refresh the view with current data."""
        # Update profile selector
        profiles = self._profile_service.get_all_profiles()
        current_profile = self._profile_service.get_current_profile()
        self._profile_selector.set_profiles(profiles, current_profile)
        
        # Get links from current profile
        all_links = self._profile_service.get_links()

        # Apply search filter with tag filters
        tag_filters = self._search_bar.get_active_tag_filters()
        if self._current_search_term or tag_filters:
            # Use first tag filter (or None if no filters)
            tag_filter = tag_filters[0] if tag_filters else None
            filtered_links = self._profile_service.search_links(
                self._current_search_term, tag_filter=tag_filter
            )

            # Apply additional tag filters if multiple (AND logic)
            if len(tag_filters) > 1:
                for tag in tag_filters[1:]:
                    filtered_links = [link for link in filtered_links if link.has_tag(tag)]
        else:
            filtered_links = all_links
        
        # Apply sorting
        if self._current_sort_column:
            filtered_links = self._profile_service.sort_links(
                filtered_links, self._current_sort_column, self._current_sort_reverse
            )
        
        # Store current filtered links
        self._current_filtered_links = filtered_links
        
        # Update UI components
        self._link_list_view.set_links(all_links, filtered_links)
        self._link_list_view.set_sort_column(self._current_sort_column, self._current_sort_reverse)
        
        # Update result count
        self._search_bar.set_result_count(len(filtered_links), len(all_links))
    
    def _get_selected_indices(self) -> List[int]:
        """Get currently selected link indices."""
        return self._link_list_view.get_selected_indices()
    
    def _restore_selection(self, indices: List[int]) -> None:
        """Restore selection to given indices."""
        self._link_list_view.restore_selection(indices)
    
    # Event handlers
    def _on_data_changed(self) -> None:
        """Handle data changes from the service."""
        # If we're performing a targeted selection (like opening a random link),
        # don't restore the previous selection as it will be overridden anyway
        if not self._performing_targeted_selection:
            selected_indices = self._get_selected_indices()
            self._refresh_view()
            if selected_indices:
                self._restore_selection(selected_indices)
        else:
            # Just refresh the view, targeted selection will handle its own selection
            self._refresh_view()
            # Reset the flag after the refresh
            self._performing_targeted_selection = False
    
    def _on_profile_changed(self, profile_name: str) -> None:
        """Handle profile selection change."""
        if self._profile_service.switch_to_profile(profile_name):
            # Clear search and sort when switching profiles
            self._current_search_term = ""
            self._current_sort_column = None
            self._current_sort_reverse = False
            self._search_bar.clear_search()
            self._refresh_view()
            # Auto-select first item when switching profiles
            self._link_list_view.focus(auto_select_first=True)
    
    def _on_manage_profiles(self) -> None:
        """Show the profile management dialog."""
        profiles = self._profile_service.get_all_profiles()
        current_profile = self._profile_service.get_current_profile()
        
        dialog = ProfileManagerDialog(self._root, profiles, current_profile)
        dialog.set_callbacks(
            on_create=self._profile_service.create_profile,
            on_rename=self._profile_service.rename_profile,
            on_delete=self._profile_service.delete_profile,
            on_set_default=self._profile_service.set_default_profile
        )
        
        # Refresh the dialog with updated data after each operation
        def refresh_dialog():
            updated_profiles = self._profile_service.get_all_profiles()
            updated_current = self._profile_service.get_current_profile()
            dialog.update_profiles(updated_profiles, updated_current)
        
        # Override the refresh method to actually refresh
        dialog._refresh_profiles = refresh_dialog
        
        dialog.show()
        # Refresh our view after dialog closes
        self._refresh_view()
    
    def _on_search_changed(self, search_term: str) -> None:
        """Handle search term changes."""
        self._current_search_term = search_term
        self._refresh_view()
    
    def _on_search_cleared(self) -> None:
        """Handle search being cleared."""
        self._current_search_term = ""
        self._refresh_view()

    def _on_filter_changed(self) -> None:
        """Handle tag filter changes."""
        self._refresh_view()
    
    def _on_links_double_clicked(self, indices: List[int]) -> None:
        """Handle double-click on links."""
        if indices:
            self._profile_service.open_links(indices)
    
    def _delete_selected(self) -> None:
        """Delete currently selected links (wrapper for vim key binding)."""
        indices = self._get_selected_indices()
        if indices:
            self._on_delete_key_pressed(indices)

    def _on_delete_key_pressed(self, indices: List[int]) -> None:
        """Handle delete key press and save to undo stack."""
        if not indices:
            return

        # Always show confirmation dialog
        if len(indices) == 1:
            confirmation_message = "Are you sure you want to delete this link?"
        else:
            confirmation_message = f"Are you sure you want to delete {len(indices)} selected link(s)?"

        if not messagebox.askyesno("Confirm Deletion", confirmation_message):
            return

        # Get the visual position of the first selected item before deletion
        visual_positions = self._link_list_view.get_visual_positions_of_selected()
        if not visual_positions:
            return

        first_visual_position = min(visual_positions)

        # Remember the links for undo
        links = self._profile_service.get_links()
        deleted_links = [links[i] for i in sorted(indices)]
        self._undo_stack.append((sorted(indices), deleted_links))

        # Delete the links
        self._profile_service.delete_links(indices)

        # Smart refocusing: select the item at the same visual position
        # If we deleted the last item(s), select the new last item
        remaining_links = self._profile_service.get_links()
        if remaining_links:
            # Get total number of visible items after deletion
            # (accounting for any active search filter)
            all_items = self._link_list_view._tree.get_children()
            total_visible = len(all_items)

            if total_visible > 0:
                # Stay at the same visual position, or go to the last item if we deleted beyond the end
                new_visual_position = min(first_visual_position, total_visible - 1)
                self._link_list_view.select_by_visual_position(new_visual_position)
        else:
            # No links left, just clear selection
            self._link_list_view.clear_selection()
    
    def _on_sort_requested(self, column: str, reverse: bool) -> None:
        """Handle sort request."""
        self._current_sort_column = column
        self._current_sort_reverse = reverse
        self._refresh_view()
    
    def _on_escape_pressed(self, event) -> None:
        """Handle escape key press based on which widget has focus."""
        # Clear numeric buffer first if present
        if self._numeric_buffer:
            self._clear_numeric_buffer()
            return

        if self._search_bar.has_focus():
            # Search bar has focus - clear search
            self._search_bar.clear_search()
        elif self._link_list_view.has_focus():
            # Tree view has focus - clear selection
            self._link_list_view.clear_selection()
        else:
            # Fallback: if search has text, clear it; otherwise clear selection
            if self._search_bar.get_search_term():
                self._search_bar.clear_search()
            else:
                self._link_list_view.clear_selection()

    def _on_number_key_pressed(self, event) -> str:
        """Handle number key press for vim-style multiplier."""
        # Don't capture numbers when typing in search bar
        if self._search_bar.has_focus():
            return

        # Add to numeric buffer
        self._numeric_buffer += event.char
        self._update_numeric_display()
        return "break"  # Prevent default behavior

    def _update_numeric_display(self) -> None:
        """Update the numeric buffer display."""
        if self._numeric_buffer:
            self._numeric_label.config(text=f"[{self._numeric_buffer}]")
        else:
            self._numeric_label.config(text="")

    def _clear_numeric_buffer(self) -> None:
        """Clear the numeric buffer."""
        self._numeric_buffer = ""
        self._update_numeric_display()

    def _get_multiplier(self) -> int:
        """Get the current multiplier from numeric buffer, default to 1."""
        if not self._numeric_buffer:
            return 1
        try:
            multiplier = int(self._numeric_buffer)
            return max(1, multiplier)  # At least 1
        except ValueError:
            return 1

    def _execute_with_multiplier(self, func) -> None:
        """Execute a function N times based on numeric buffer."""
        multiplier = self._get_multiplier()
        self._clear_numeric_buffer()

        for _ in range(multiplier):
            func()

    def _undo_delete(self) -> None:
        """Undo the last delete operation by unarchiving links."""
        if not self._undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return

        # Pop the last delete operation
        indices, links = self._undo_stack.pop()

        # Unarchive the links (they're still in the profile, just archived)
        for link in links:
            link.unarchive()

        # Save and notify
        current_profile = self._profile_service.get_current_profile()
        if current_profile:
            self._profile_service._save_current_profile()
            self._profile_service._notify_observers()

        messagebox.showinfo("Undo", f"Restored {len(links)} link(s).")
    
    # Action methods
    def _add_links(self) -> None:
        """Show add links dialog with smart title fetching."""
        def add_links_callback(urls: List[str]) -> None:
            if not urls:
                return

            # Get all existing links (including archived) for duplicate detection
            all_links = self._profile_service.get_all_links_including_archived()
            existing_urls = {self._normalize_url_for_comparison(link.url) for link in all_links}

            # Filter out duplicates
            new_urls = []
            duplicate_count = 0
            for url in urls:
                normalized = self._normalize_url_for_comparison(url)
                if normalized not in existing_urls:
                    new_urls.append(url)
                    existing_urls.add(normalized)
                else:
                    duplicate_count += 1

            # Show message if some were duplicates
            if duplicate_count > 0:
                messagebox.showinfo("Duplicate Links",
                                  f"Skipped {duplicate_count} duplicate link(s).")

            if not new_urls:
                return

            # Add new links immediately with URL as name (in a batch)
            new_links = [Link(url, url, source="manual") for url in new_urls]
            self._profile_service.add_links_batch(new_links)

            # Then, asynchronously fetch and update titles for those that need it
            self._background_fetch_titles(new_urls)

        AddLinksDialog(self._root, add_links_callback)

    def _normalize_url_for_comparison(self, url: str) -> str:
        """
        Normalize URL for duplicate detection.
        Matches the normalization used in ScraperService.
        """
        url = url.strip().lower()
        # Add https:// if no protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        # Normalize protocol to https
        if url.startswith('http://'):
            url = 'https://' + url[7:]
        # Remove trailing slash
        if url.endswith('/'):
            url = url[:-1]
        # Remove www. prefix for comparison
        url = url.replace('://www.', '://')
        return url

    def _background_fetch_titles(self, urls: List[str]) -> None:
        """Fetch titles concurrently in background for URLs that need it."""
        def fetch_and_update():
            all_links = self._profile_service.get_links()

            # Identify which URLs need title fetching
            urls_to_fetch = []
            for url in urls:
                for link in all_links:
                    if link.url == url and TitleFetcher.should_fetch_title(url, link.name):
                        urls_to_fetch.append(url)
                        break

            if not urls_to_fetch:
                return

            # Fetch titles concurrently
            updates = TitleFetcher.fetch_titles_concurrent(urls_to_fetch)

            # Apply updates on main thread
            if updates:
                self._root.after(0, lambda: self._apply_title_updates(updates))

        # Run in background thread
        thread = threading.Thread(target=fetch_and_update, daemon=True)
        thread.start()

    def _apply_title_updates(self, updates: List[Tuple[str, str]]) -> None:
        """Apply title updates to links by URL lookup.

        Uses URL-based lookup instead of indices to avoid stale-index bugs
        when the link list changes during background title fetching.
        Creates new Link instances to avoid mutating live objects.
        """
        all_links = self._profile_service.get_links()

        # Prepare batch updates by finding each URL in the current list
        batch_updates = []
        for url, new_title in updates:
            for i, link in enumerate(all_links):
                if link.url == url:
                    updated_link = Link(
                        name=new_title,
                        url=link.url,
                        favorite=link.favorite,
                        date_added=link.date_added,
                        last_opened=link.last_opened,
                        open_count=link.open_count,
                        archived=link.archived,
                        first_opened=link.first_opened,
                        favorite_toggle_count=link.favorite_toggle_count,
                        last_modified=datetime.now().isoformat(),
                        time_to_first_open=link.time_to_first_open,
                        opens_last_30_days=link.opens_last_30_days,
                        tags=link.tags.copy(),
                        category=link.category,
                        domain=link.domain,
                        notes=link.notes,
                        source=link.source,
                        auto_named=True,
                        link_status=link.link_status,
                        last_checked=link.last_checked,
                        http_status_code=link.http_status_code,
                    )
                    batch_updates.append((i, updated_link))
                    break

        # Apply all updates in a single batch (one save, one UI refresh)
        if batch_updates:
            self._profile_service.update_links_batch(batch_updates)

    def _scan_and_update_titles(self) -> None:
        """Background scan of existing links to update titles where needed."""
        all_links = self._profile_service.get_links()

        # Collect URLs that need title updates
        urls_to_fetch = [
            link.url for link in all_links
            if TitleFetcher.should_fetch_title(link.url, link.name)
        ]

        if not urls_to_fetch:
            return

        # Fetch concurrently in background
        def fetch_all():
            updates = TitleFetcher.fetch_titles_concurrent(urls_to_fetch)

            if updates:
                self._root.after(0, lambda: self._apply_title_updates(updates))

        thread = threading.Thread(target=fetch_all, daemon=True)
        thread.start()

    def _manual_scan_titles(self) -> None:
        """Manually trigger a scan for title updates."""
        all_links = self._profile_service.get_links()

        # Count how many links would be updated
        count = sum(1 for link in all_links
                   if TitleFetcher.should_fetch_title(link.url, link.name))

        if count == 0:
            auto_named_count = sum(1 for link in all_links if link.auto_named)
            if auto_named_count > 0:
                messagebox.showinfo("Scan Titles",
                                  f"All links already have good titles!\n\n"
                                  f"({auto_named_count} links were auto-named. "
                                  f"Press Shift+R to force refresh them.)")
            else:
                messagebox.showinfo("Scan Titles", "All links already have good titles!")
            return

        if messagebox.askyesno("Scan Titles",
                              f"Found {count} link(s) that could use better titles.\n"
                              "Fetch titles from the web?\n\n"
                              "(This will only update links with URL-based names)"):
            self._scan_and_update_titles()
            messagebox.showinfo("Scan Titles",
                              f"Fetching titles for {count} link(s) in background...")

    def _force_refresh_titles(self) -> None:
        """Force re-fetch titles for all links with streaming approval dialog."""
        all_links = self._profile_service.get_links()

        if not all_links:
            messagebox.showinfo("Force Refresh Titles",
                              "No links found to refresh.")
            return

        if not messagebox.askyesno(
            "Force Refresh Titles",
            f"Fetch web titles for all {len(all_links)} link(s)?\n\n"
            "You'll be able to review and approve each change "
            "before it's applied."
        ):
            return

        # Open the approval dialog immediately — results stream in live
        dialog = TitleApprovalDialog(self._root, total=len(all_links))

        # Build a url→name map for comparing results
        link_names = {link.url: link.name for link in all_links}
        urls = list(link_names.keys())

        def on_result(url: str, title: Optional[str]) -> None:
            """Called from worker threads for each completed fetch."""
            current_name = link_names.get(url, "")
            if title and title != current_name:
                self._root.after(0, lambda u=url, c=current_name, t=title:
                                 dialog.add_change(u, c, t))
            self._root.after(0, dialog.increment_progress)

        def fetch_all() -> None:
            TitleFetcher.fetch_titles_concurrent(urls, on_result=on_result)
            self._root.after(0, dialog.mark_complete)

        thread = threading.Thread(target=fetch_all, daemon=True)
        thread.start()

        # Block until the user closes the dialog
        approved = dialog.wait()

        if approved:
            self._apply_title_updates(approved)
            messagebox.showinfo("Force Refresh Titles",
                              f"Updated {len(approved)} link title(s).")

    def _run_scraper_on_startup(self) -> None:
        """Run scraper unconditionally on application startup."""
        if not self._scraper_service:
            return

        # Show scraper status if dialog exists
        if self._scraper_status_dialog and tk.Toplevel.winfo_exists(self._scraper_status_dialog._dialog):
            domain = self._scraper_service._state.get("target_domain", "fyptt.to")
            self._scraper_status_dialog.start_scraping(domain)

        def scrape_in_background():
            result = self._scraper_service.run_scheduled_scrape()
            # Schedule UI update on main thread
            if result:
                self._root.after(0, lambda: self._on_scrape_completed(result))

        # Run in daemon thread (follow pattern from _background_fetch_titles)
        thread = threading.Thread(target=scrape_in_background, daemon=True)
        thread.start()

        # Schedule periodic checks starting 1 hour after startup
        self._root.after(3600000, self._run_scraper_if_needed)

    def _run_scraper_if_needed(self) -> None:
        """Check and run scraper if 24 hours elapsed since last run."""
        if not self._scraper_service or not self._scraper_service.should_run_scrape():
            # Schedule next check in 1 hour
            if self._scraper_service:
                self._root.after(3600000, self._run_scraper_if_needed)
            return

        # Show scraper status if dialog exists
        if self._scraper_status_dialog and tk.Toplevel.winfo_exists(self._scraper_status_dialog._dialog):
            domain = self._scraper_service._state.get("target_domain", "fyptt.to")
            self._scraper_status_dialog.start_scraping(domain)

        def scrape_in_background():
            result = self._scraper_service.run_scheduled_scrape()
            # Schedule UI update on main thread
            if result:
                self._root.after(0, lambda: self._on_scrape_completed(result))

        # Run in daemon thread (follow pattern from _background_fetch_titles)
        thread = threading.Thread(target=scrape_in_background, daemon=True)
        thread.start()

        # Schedule next check in 1 hour
        self._root.after(3600000, self._run_scraper_if_needed)

    def _on_scrape_completed(self, result: dict) -> None:
        """Handle scrape completion."""
        if result.get('new_links', 0) > 0:
            print(f"Scraper: Added {result['new_links']} new links from {result.get('domain', 'unknown')}")
            # Fetch titles for newly added links that still have URL-as-name
            all_links = self._profile_service.get_links()
            urls_needing_titles = [
                link.url for link in all_links
                if TitleFetcher.should_fetch_title(link.url, link.name)
            ]
            if urls_needing_titles:
                self._background_fetch_titles(urls_needing_titles)

        # Update scraper status dialog if it exists
        if self._scraper_status_dialog and tk.Toplevel.winfo_exists(self._scraper_status_dialog._dialog):
            self._scraper_status_dialog.scraping_complete(
                urls_found=result.get('total_urls_found', 0),
                links_added=result.get('new_links', 0),
                duplicates=result.get('skipped_duplicates', 0)
            )

    def _edit_link(self) -> None:
        """Show edit link dialog."""
        indices = self._get_selected_indices()
        if not indices:
            return
        if len(indices) > 1:
            messagebox.showinfo("Info", "Please select only one item to edit.")
            return
        
        link_index = indices[0]
        links = self._profile_service.get_links()
        if link_index >= len(links):
            return
        
        link = links[link_index]
        
        def on_save(updated_link: Link) -> None:
            self._profile_service.update_link(link_index, updated_link)

        EditLinkDialog(self._root, link, on_save, get_all_tags=self._profile_service.get_all_tags)
    
    def _toggle_favorite(self) -> None:
        """Toggle favorite status of selected links."""
        indices = self._get_selected_indices()
        for index in indices:
            self._profile_service.toggle_favorite(index)
    
    def _toggle_read_status(self) -> None:
        """Toggle read status of selected links."""
        indices = self._get_selected_indices()
        links = self._profile_service.get_links()

        for index in indices:
            if index < len(links):
                link = links[index]
                if link.is_unread():
                    link.mark_as_opened()
                else:
                    link.last_opened = None
                self._profile_service.update_link(index, link)

    def _bulk_add_tags(self) -> None:
        """Add tags to selected links."""
        indices = self._get_selected_indices()
        if not indices:
            messagebox.showinfo("Info", "No links selected.")
            return

        # Simple input dialog for tags
        from tkinter import simpledialog
        tags_input = simpledialog.askstring(
            "Add Tags",
            f"Enter tags to add to {len(indices)} selected link(s)\n(comma-separated):",
            parent=self._root
        )

        if tags_input:
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            if tags:
                self._profile_service.add_tags_to_links(indices, tags)
                messagebox.showinfo("Success", f"Added {len(tags)} tag(s) to {len(indices)} link(s).")

    def _bulk_remove_tags(self) -> None:
        """Remove tags from selected links."""
        indices = self._get_selected_indices()
        if not indices:
            messagebox.showinfo("Info", "No links selected.")
            return

        # Get all tags from selected links
        links = self._profile_service.get_links()
        all_tags = set()
        for index in indices:
            if index < len(links):
                all_tags.update(links[index].tags)

        if not all_tags:
            messagebox.showinfo("Info", "Selected links have no tags.")
            return

        # Simple input dialog for tags
        from tkinter import simpledialog
        tags_input = simpledialog.askstring(
            "Remove Tags",
            f"Enter tags to remove from {len(indices)} selected link(s)\n(comma-separated):\n\nAvailable: {', '.join(sorted(all_tags))}",
            parent=self._root
        )

        if tags_input:
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            if tags:
                self._profile_service.remove_tags_from_links(indices, tags)
                messagebox.showinfo("Success", f"Removed {len(tags)} tag(s) from {len(indices)} link(s).")

    def _manage_tags(self) -> None:
        """Open the tag manager dialog."""
        TagManagerDialog(
            self._root,
            get_all_links=self._profile_service.get_links,
            update_link=self._profile_service.update_link,
            on_filter_by_tag=self._search_bar.add_tag_filter
        )

    def _weighted_random_choice(self, indices: List[int], links: List[Link]) -> int:
        """
        Select a random index from the given indices using weighted probability.
        Links with lower open_count have higher probability of being selected.

        Weight formula: 1 / (open_count + 1)
        - Never opened (count=0): weight = 1.0
        - Opened once (count=1): weight = 0.5
        - Opened twice (count=2): weight = 0.33
        - And so on...

        Args:
            indices: List of valid indices to choose from
            links: The full list of links

        Returns:
            The selected index
        """
        import random

        # Calculate weights for each index
        weights = []
        for idx in indices:
            link = links[idx]
            # Inverse weight: less opened = higher weight
            weight = 1.0 / (link.open_count + 1)
            weights.append(weight)

        # Use random.choices with weights (returns list, so take first element)
        selected_index = random.choices(indices, weights=weights, k=1)[0]
        return selected_index

    def _open_random(self) -> None:
        """Open a random link (weighted by open_count) and select it in the UI."""
        links = self._profile_service.get_links()
        if not links:
            messagebox.showinfo("Info", "No links available.")
            return

        indices = list(range(len(links)))
        index = self._weighted_random_choice(indices, links)

        # Set flag to prevent selection restoration during data change
        self._performing_targeted_selection = True
        self._profile_service.open_links([index])
        self._link_list_view.select_and_scroll_to(index)

    def _open_random_unread(self) -> None:
        """Open a random unread link and select it in the UI."""
        links = self._profile_service.get_links()
        unread_indices = [i for i, link in enumerate(links) if link.is_unread()]

        if not unread_indices:
            messagebox.showinfo("Info", "No unread links available.")
            return

        # For unread links, all have open_count=0, so weights are equal (true random)
        index = self._weighted_random_choice(unread_indices, links)

        # Set flag to prevent selection restoration during data change
        self._performing_targeted_selection = True
        self._profile_service.open_links([index])
        self._link_list_view.select_and_scroll_to(index)

    def _open_random_favorite(self) -> None:
        """Open a random favorite link (weighted by open_count) and select it in the UI."""
        links = self._profile_service.get_links()
        favorite_indices = [i for i, link in enumerate(links) if link.favorite]

        if not favorite_indices:
            messagebox.showinfo("Info", "No favorite links available.")
            return

        index = self._weighted_random_choice(favorite_indices, links)

        # Set flag to prevent selection restoration during data change
        self._performing_targeted_selection = True
        self._profile_service.open_links([index])
        self._link_list_view.select_and_scroll_to(index)
    
    def _focus_table(self) -> None:
        """Give focus to the link table."""
        self._link_list_view.focus()
    
    def _on_tab_pressed(self, event) -> str:
        """Handle Tab key to switch focus between search bar and table."""
        if self._search_bar.has_focus():
            # Switch from search bar to table
            self._link_list_view.focus()
        else:
            # Switch from table to search bar
            self._search_bar.focus()
        return "break"  # Prevent default tab behavior

    def _on_open_all_clicked(self) -> None:
        """Handle open all button click."""
        if not self._current_filtered_links:
            messagebox.showinfo("No Links", "No links to open.")
            return
        
        link_count = len(self._current_filtered_links)
        if link_count > 10:
            if not messagebox.askyesno("Confirm Open All", 
                                     f"Are you sure you want to open {link_count} links? This might open many browser tabs."):
                return
        
        # Get indices of filtered links in the original list
        all_links = self._profile_service.get_links()
        indices = []
        for filtered_link in self._current_filtered_links:
            try:
                index = all_links.index(filtered_link)
                indices.append(index)
            except ValueError:
                continue
        
        if indices:
            self._profile_service.open_links(indices)

    def _open_selected(self) -> None:
        """Open selected links."""
        indices = self._get_selected_indices()
        if indices:
            self._profile_service.open_links(indices)
    
    def _export_links(self) -> None:
        """Export all links from all profiles to a file."""
        try:
            self._import_export_service.export_all_links()
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export links: {str(e)}")
    
    def _import_links(self) -> None:
        """Import links from a file."""
        try:
            success = self._import_export_service.import_links()
            if success:
                # Refresh the view to show imported data
                self._refresh_view()
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import links: {str(e)}")

    def _deduplicate_links(self) -> None:
        """Find and merge duplicate links in the current profile."""
        try:
            current_profile = self._profile_service.get_current_profile()
            if not current_profile:
                messagebox.showinfo("No Profile", "No profile is currently loaded.")
                return

            if len(current_profile.links) == 0:
                messagebox.showinfo("No Links", "The current profile has no links to deduplicate.")
                return

            # Find duplicates
            duplicate_groups = self._deduplication_service.find_duplicates(current_profile)

            if not duplicate_groups:
                messagebox.showinfo("No Duplicates", "No duplicate links found in the current profile.")
                return

            # Show preview dialog
            preview_dialog = DeduplicationPreviewDialog(self._root, duplicate_groups)
            confirmed = preview_dialog.show()

            if not confirmed:
                return  # User cancelled

            # Show progress dialog
            total_groups = len(duplicate_groups)
            progress_dialog = DeduplicationProgressDialog(self._root, total_groups)

            # Perform automatic deduplication
            progress_dialog.update(0, "Auto-merging duplicate groups...")
            self._root.update()

            auto_merged, removed, conflicts = self._deduplication_service.deduplicate_profile(current_profile)

            progress_dialog.update(auto_merged, f"Auto-merged {auto_merged} groups")
            self._root.update()

            # Handle conflicts that need manual resolution
            manually_merged = 0
            skipped = 0

            if conflicts:
                progress_dialog.close()

            for idx, (link1, link2) in enumerate(conflicts, 1):
                # Show conflict resolution dialog
                conflict_dialog = MergeConflictDialog(self._root, link1, link2)
                result = conflict_dialog.show()

                if not result:
                    # Dialog was closed without making a choice
                    skipped += 1
                    continue

                choice, custom_name = result

                if choice == "cancel":
                    # User wants to cancel the entire operation
                    messagebox.showinfo(
                        "Deduplication Cancelled",
                        f"Deduplication cancelled. {auto_merged} groups were already merged before cancellation."
                    )
                    # Save current state and refresh
                    self._profile_service._profile_repository.update(current_profile)
                    self._refresh_view()
                    return

                elif choice == "skip":
                    # Keep both links
                    skipped += 1
                    continue

                else:
                    # Merge the links with user's choice
                    merged_link = self._deduplication_service.merge_links_manual(
                        link1, link2, choice, custom_name
                    )

                    # Find and remove both original links by index
                    non_archived_links = current_profile.links
                    try:
                        idx1 = non_archived_links.index(link1)
                        current_profile.remove_link(idx1)
                        removed += 1
                        # Re-get list after removal
                        non_archived_links = current_profile.links
                    except ValueError:
                        pass

                    try:
                        idx2 = non_archived_links.index(link2)
                        current_profile.remove_link(idx2)
                        removed += 1
                    except ValueError:
                        pass

                    # Add merged link
                    current_profile.add_link(merged_link)
                    manually_merged += 1

            # Close progress dialog if still open
            if not conflicts:
                progress_dialog.close()

            # Save the updated profile
            self._profile_service._profile_repository.update(current_profile)

            # Refresh the view
            self._refresh_view()

            # Show results dialog
            results_dialog = DeduplicationResultsDialog(
                self._root,
                auto_merged,
                removed,
                manually_merged,
                skipped
            )
            results_dialog.show()

        except Exception as e:
            messagebox.showerror("Deduplication Error", f"Failed to deduplicate links: {str(e)}")
            import traceback
            traceback.print_exc()

    def _show_analytics(self) -> None:
        """Show analytics dialog."""
        try:
            current_profile = self._profile_service.get_current_profile()
            all_profiles = self._profile_service.get_all_profiles()

            if not current_profile:
                messagebox.showinfo("No Profile", "No profile is currently loaded.")
                return

            # Create analytics service
            analytics_service = AnalyticsService(self._profile_service)

            # Import browser service for opening links from analytics dialog
            from services.browser_service import SystemBrowserService
            browser_service = SystemBrowserService()

            dialog = AnalyticsDialog(
                self._root,
                current_profile,
                all_profiles,
                analytics_service,
                browser_service,
                self._profile_service
            )
            dialog.show()
        except Exception as e:
            messagebox.showerror("Analytics Error", f"Failed to open analytics: {str(e)}")

    def _show_help(self) -> None:
        """Show keyboard shortcuts help dialog."""
        HelpDialog(self._root)

    def _show_scraper_status(self) -> None:
        """Show or create the scraper status dialog."""
        if self._scraper_status_dialog is None or not tk.Toplevel.winfo_exists(self._scraper_status_dialog._dialog):
            self._scraper_status_dialog = ScraperStatusDialog(self._root, self._scraper_service)

            # Connect scraper logging to dialog
            if self._scraper_service:
                # Create a thread-safe logging callback
                def log_to_dialog(message: str, prefix: str = "•"):
                    # Schedule log update on main thread
                    self._root.after(0, lambda: self._scraper_status_dialog.add_log(message, prefix))

                self._scraper_service.set_log_callback(log_to_dialog)

            # Load last run info from scraper service
            if self._scraper_service:
                info = self._scraper_service.get_last_run_info()
                if info.get('last_run'):
                    self._scraper_status_dialog.add_log(
                        f"Last run: {info['last_run']}", "ℹ"
                    )
                    self._scraper_status_dialog.add_log(
                        f"Found {info.get('last_url_count', 0)} URLs", "→"
                    )
                if info.get('paused'):
                    self._scraper_status_dialog.add_log("Scraper is paused", "⏸")
        else:
            # Bring existing dialog to front
            self._scraper_status_dialog._dialog.lift()

    def _show_archived_links(self) -> None:
        """Show archived links dialog."""
        current_profile = self._profile_service.get_current_profile()
        if not current_profile:
            messagebox.showinfo("No Profile", "No profile is currently loaded.")
            return

        archived_links = current_profile.get_archived_links()
        if not archived_links:
            messagebox.showinfo("No Archived Links", "There are no archived links in the current profile.")
            return

        def on_restore(restored_links: List[Link]) -> None:
            """Handle restoration of archived links."""
            # Save changes
            self._profile_service._save_current_profile()
            self._profile_service._notify_observers()

        ArchivedLinksDialog(self._root, archived_links, on_restore)

    def _toggle_scraper_pause(self) -> None:
        """Toggle the scraper pause state."""
        if not self._scraper_service:
            messagebox.showinfo("Scraper", "Scraper service is not available.")
            return

        is_paused = self._scraper_service.toggle_pause()
        status = "paused" if is_paused else "resumed"
        messagebox.showinfo("Scraper", f"Scraper {status}.")