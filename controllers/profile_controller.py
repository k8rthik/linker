import tkinter as tk
from tkinter import messagebox
from typing import List, Optional, Tuple
from collections import deque
import threading
from models.link import Link
from models.profile import Profile
from services.profile_service import ProfileService
from services.import_export_service import ImportExportService
from ui.components.link_list_view import LinkListView
from ui.components.search_bar import SearchBar
from ui.components.profile_selector import ProfileSelector
from ui.dialogs.edit_dialog import EditLinkDialog
from ui.dialogs.add_links_dialog import AddLinksDialog
from ui.dialogs.profile_manager_dialog import ProfileManagerDialog
from ui.dialogs.analytics_dialog import AnalyticsDialog
from utils.title_fetcher import TitleFetcher


class ProfileController:
    """Controller for managing profiles and their links with UI interactions."""
    
    def __init__(self, root: tk.Tk, profile_service: ProfileService,
                 scraper_service: Optional['ScraperService'] = None):
        self._root = root
        self._profile_service = profile_service
        self._scraper_service = scraper_service
        self._import_export_service = ImportExportService(profile_service)
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
        
        # Register as observer
        self._profile_service.add_observer(self._on_data_changed)

        self._create_ui()
        self._setup_callbacks()
        self._refresh_view()
        # Auto-select first item on initial load
        self._link_list_view.focus(auto_select_first=True)

        # Background scan for title updates (runs after UI is ready)
        self._root.after(1000, self._scan_and_update_titles)  # Wait 1 second after startup

        # Run scraper if needed (5 seconds after startup, after titles start fetching)
        if self._scraper_service:
            self._root.after(5000, self._run_scraper_if_needed)
    
    def _create_ui(self) -> None:
        """Create the user interface."""
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
        
        # Link list view callbacks
        self._link_list_view.set_double_click_callback(self._on_links_double_clicked)
        self._link_list_view.set_delete_key_callback(self._on_delete_key_pressed)
        self._link_list_view.set_space_key_callback(self._open_selected)
        self._link_list_view.set_sort_callback(self._on_sort_requested)
    
    def _setup_keyboard_shortcuts(self) -> None:
        """Setup global keyboard shortcuts."""
        self._search_bar.bind_keyboard_shortcuts(self._root)
        self._link_list_view.bind_keyboard_shortcuts(self._root)

        # Escape key handling
        self._root.bind("<Escape>", self._on_escape_pressed)

        # Number keys for vim-style prefix (0-9)
        for num in range(10):
            self._root.bind(str(num), self._on_number_key_pressed)

        # Additional shortcuts
        import sys
        if sys.platform == "darwin":
            # macOS shortcuts (using Command key)
            self._root.bind("<Command-d>", lambda e: self._execute_with_multiplier(self._toggle_favorite))
            self._root.bind("<Command-e>", lambda e: self._execute_with_multiplier(self._toggle_read_status))
            self._root.bind("<Command-r>", lambda e: self._execute_with_multiplier(self._open_random))
            self._root.bind("<Command-Shift-F>", lambda e: self._execute_with_multiplier(self._open_random_favorite))
            self._root.bind("<Command-u>", lambda e: self._execute_with_multiplier(self._open_random_unread))
            self._root.bind("<Command-l>", lambda e: self._focus_table())
            self._root.bind("<Command-p>", lambda e: self._on_manage_profiles())
            self._root.bind("<Command-n>", lambda e: self._add_links())
            self._root.bind("<Command-z>", lambda e: self._undo_delete())
            self._root.bind("<Command-Shift-t>", lambda e: self._manual_scan_titles())
        else:
            # Windows/Linux shortcuts (using Ctrl key)
            self._root.bind("<Control-d>", lambda e: self._execute_with_multiplier(self._toggle_favorite))
            self._root.bind("<Control-e>", lambda e: self._execute_with_multiplier(self._toggle_read_status))
            self._root.bind("<Control-r>", lambda e: self._execute_with_multiplier(self._open_random))
            self._root.bind("<Control-Shift-F>", lambda e: self._execute_with_multiplier(self._open_random_favorite))
            self._root.bind("<Control-u>", lambda e: self._execute_with_multiplier(self._open_random_unread))
            self._root.bind("<Control-l>", lambda e: self._focus_table())
            self._root.bind("<Control-p>", lambda e: self._on_manage_profiles())
            self._root.bind("<Control-n>", lambda e: self._add_links())
            self._root.bind("<Control-z>", lambda e: self._undo_delete())
            self._root.bind("<Control-Shift-t>", lambda e: self._manual_scan_titles())

        # Platform-independent shortcuts
        self._root.bind("<Return>", lambda e: self._edit_link())
        self._root.bind("<Tab>", self._on_tab_pressed)
    
    def _refresh_view(self) -> None:
        """Refresh the view with current data."""
        # Update profile selector
        profiles = self._profile_service.get_all_profiles()
        current_profile = self._profile_service.get_current_profile()
        self._profile_selector.set_profiles(profiles, current_profile)
        
        # Get links from current profile
        all_links = self._profile_service.get_links()
        
        # Apply search filter
        if self._current_search_term:
            filtered_links = self._profile_service.search_links(self._current_search_term)
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
    
    def _on_links_double_clicked(self, indices: List[int]) -> None:
        """Handle double-click on links."""
        if indices:
            self._profile_service.open_links(indices)
    
    def _on_delete_key_pressed(self, indices: List[int]) -> None:
        """Handle delete key press and save to undo stack."""
        if not indices:
            return

        if len(indices) > 1:
            if not messagebox.askyesno("Confirm Deletion",
                                     f"Are you sure you want to delete {len(indices)} selected link(s)?"):
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
        """Undo the last delete operation."""
        if not self._undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return

        # Pop the last delete operation
        indices, links = self._undo_stack.pop()

        # Re-insert the links at their original positions
        all_links = self._profile_service.get_links()

        # Sort indices in reverse to maintain correct positions during insertion
        for index, link in sorted(zip(indices, links), reverse=True):
            # Insert at the original position (clamped to valid range)
            insert_pos = min(index, len(all_links))
            all_links.insert(insert_pos, link)

        # Update the profile with restored links
        current_profile = self._profile_service.get_current_profile()
        if current_profile:
            current_profile.links = all_links
            self._profile_service._repository.update(current_profile)
            self._profile_service._notify_observers()

        messagebox.showinfo("Undo", f"Restored {len(links)} link(s).")
    
    # Action methods
    def _add_links(self) -> None:
        """Show add links dialog with smart title fetching."""
        def add_links_callback(urls: List[str]) -> None:
            if not urls:
                return

            # First, add all links immediately with URL as name
            for url in urls:
                link = Link(url, url)  # Temporary: name = url
                self._profile_service.add_link(link)

            # Then, asynchronously fetch and update titles for those that need it
            self._background_fetch_titles(urls)

        AddLinksDialog(self._root, add_links_callback)

    def _background_fetch_titles(self, urls: List[str]) -> None:
        """Fetch titles in background for URLs that need it."""
        def fetch_and_update():
            all_links = self._profile_service.get_links()

            # Find the newly added links and check which need title fetching
            updates = []
            for url in urls:
                # Find the link with this URL
                for i, link in enumerate(all_links):
                    if link.url == url and TitleFetcher.should_fetch_title(url, link.name):
                        # Fetch the title
                        title = TitleFetcher.fetch_title(url)
                        if title:
                            updates.append((i, title))
                        break

            # Apply updates on main thread
            if updates:
                self._root.after(0, lambda: self._apply_title_updates(updates))

        # Run in background thread
        thread = threading.Thread(target=fetch_and_update, daemon=True)
        thread.start()

    def _apply_title_updates(self, updates: List[Tuple[int, str]]) -> None:
        """Apply title updates to links."""
        all_links = self._profile_service.get_links()

        for index, new_title in updates:
            if index < len(all_links):
                link = all_links[index]
                link.name = new_title
                self._profile_service.update_link(index, link)

    def _scan_and_update_titles(self) -> None:
        """Background scan of existing links to update titles where needed."""
        all_links = self._profile_service.get_links()

        # Find links that need title updates
        links_to_fetch = []
        for i, link in enumerate(all_links):
            if TitleFetcher.should_fetch_title(link.url, link.name):
                links_to_fetch.append((i, link.url))

        if not links_to_fetch:
            return

        # Fetch in background
        def fetch_all():
            updates = []
            for index, url in links_to_fetch:
                title = TitleFetcher.fetch_title(url)
                if title:
                    updates.append((index, title))

            # Apply updates on main thread
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
            messagebox.showinfo("Scan Titles", "All links already have good titles!")
            return

        if messagebox.askyesno("Scan Titles",
                              f"Found {count} link(s) that could use better titles.\n"
                              "Fetch titles from the web?\n\n"
                              "(This will only update links with URL-based names)"):
            self._scan_and_update_titles()
            messagebox.showinfo("Scan Titles",
                              f"Fetching titles for {count} link(s) in background...")

    def _run_scraper_if_needed(self) -> None:
        """Check and run scraper if 24 hours elapsed since last run."""
        if not self._scraper_service or not self._scraper_service.should_run_scrape():
            # Schedule next check in 1 hour
            if self._scraper_service:
                self._root.after(3600000, self._run_scraper_if_needed)
            return

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
        
        EditLinkDialog(self._root, link, on_save)
    
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
    
    def _open_random(self) -> None:
        """Open a random link and select it in the UI."""
        links = self._profile_service.get_links()
        if not links:
            messagebox.showinfo("Info", "No links available.")
            return
        
        import random
        index = random.randint(0, len(links) - 1)
        
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
        
        import random
        index = random.choice(unread_indices)
        
        # Set flag to prevent selection restoration during data change
        self._performing_targeted_selection = True
        self._profile_service.open_links([index])
        self._link_list_view.select_and_scroll_to(index)
    
    def _open_random_favorite(self) -> None:
        """Open a random favorite link and select it in the UI."""
        links = self._profile_service.get_links()
        favorite_indices = [i for i, link in enumerate(links) if link.favorite]
        
        if not favorite_indices:
            messagebox.showinfo("Info", "No favorite links available.")
            return
        
        import random
        index = random.choice(favorite_indices)
        
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

    def _show_analytics(self) -> None:
        """Show analytics dialog."""
        current_profile = self._profile_service.get_current_profile()
        all_profiles = self._profile_service.get_all_profiles()

        if current_profile:
            dialog = AnalyticsDialog(self._root, current_profile, all_profiles)
            dialog.show()