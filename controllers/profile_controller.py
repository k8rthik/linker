import tkinter as tk
from tkinter import messagebox
from typing import List, Optional
from models.link import Link
from models.profile import Profile
from services.profile_service import ProfileService
from ui.components.link_list_view import LinkListView
from ui.components.search_bar import SearchBar
from ui.components.profile_selector import ProfileSelector
from ui.dialogs.edit_dialog import EditLinkDialog
from ui.dialogs.add_links_dialog import AddLinksDialog
from ui.dialogs.profile_manager_dialog import ProfileManagerDialog


class ProfileController:
    """Controller for managing profiles and their links with UI interactions."""
    
    def __init__(self, root: tk.Tk, profile_service: ProfileService):
        self._root = root
        self._profile_service = profile_service
        self._current_search_term = ""
        self._current_sort_column: Optional[str] = None
        self._current_sort_reverse = False
        self._current_filtered_links: List[Link] = []
        
        # UI components
        self._profile_selector: Optional[ProfileSelector] = None
        self._search_bar: Optional[SearchBar] = None
        self._link_list_view: Optional[LinkListView] = None
        
        # Register as observer
        self._profile_service.add_observer(self._on_data_changed)
        
        self._create_ui()
        self._setup_callbacks()
        self._refresh_view()
    
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
        
        buttons = [
            ("Add Links", self._add_links),
            ("Edit", self._edit_link),
            ("Toggle Favorite", self._toggle_favorite),
            ("Mark Read/Unread", self._toggle_read_status),
            ("Open Random", self._open_random),
            ("Open Unread", self._open_random_unread)
        ]
        
        for text, command in buttons:
            tk.Button(btn_frame, text=text, command=command).pack(side=tk.LEFT, padx=5)
    
    def _setup_callbacks(self) -> None:
        """Setup callbacks for UI components."""
        # Profile selector callbacks
        self._profile_selector.set_profile_changed_callback(self._on_profile_changed)
        self._profile_selector.set_manage_profiles_callback(self._on_manage_profiles)
        
        # Search bar callbacks
        self._search_bar.set_search_change_callback(self._on_search_changed)
        self._search_bar.set_clear_callback(self._on_search_cleared)
        self._search_bar.set_open_all_callback(self._on_open_all_clicked)
        
        # Link list view callbacks
        self._link_list_view.set_double_click_callback(self._on_links_double_clicked)
        self._link_list_view.set_delete_key_callback(self._on_delete_key_pressed)
        self._link_list_view.set_space_key_callback(self._open_random_unread)
        self._link_list_view.set_sort_callback(self._on_sort_requested)
    
    def _setup_keyboard_shortcuts(self) -> None:
        """Setup global keyboard shortcuts."""
        self._search_bar.bind_keyboard_shortcuts(self._root)
        self._link_list_view.bind_keyboard_shortcuts(self._root)
        
        # Escape key handling
        self._root.bind("<Escape>", self._on_escape_pressed)
        
        # Additional shortcuts
        import sys
        if sys.platform == "darwin":
            # macOS shortcuts (using Command key)
            self._root.bind("<Command-d>", lambda e: self._toggle_favorite())
            self._root.bind("<Command-e>", lambda e: self._toggle_read_status())
            self._root.bind("<Command-r>", lambda e: self._open_random())
            self._root.bind("<Command-l>", lambda e: self._focus_table())
            self._root.bind("<Command-p>", lambda e: self._on_manage_profiles())
        else:
            # Windows/Linux shortcuts (using Ctrl key)
            self._root.bind("<Control-d>", lambda e: self._toggle_favorite())
            self._root.bind("<Control-e>", lambda e: self._toggle_read_status())
            self._root.bind("<Control-r>", lambda e: self._open_random())
            self._root.bind("<Control-l>", lambda e: self._focus_table())
            self._root.bind("<Control-p>", lambda e: self._on_manage_profiles())
        
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
                self._current_sort_column, self._current_sort_reverse
            )
        
        # Store current filtered links
        self._current_filtered_links = filtered_links
        
        # Update UI components
        self._link_list_view.set_links(all_links, filtered_links)
        self._link_list_view.set_sort_column(self._current_sort_column, self._current_sort_reverse)
        self._search_bar.set_result_count(len(filtered_links), len(all_links))
        
        # Give focus to table if it's the first time or no search is active
        if not self._current_search_term and not self._search_bar.has_focus():
            self._link_list_view.focus()
    
    def _get_selected_indices(self) -> List[int]:
        """Get currently selected link indices."""
        return self._link_list_view.get_selected_indices()
    
    def _restore_selection(self, indices: List[int]) -> None:
        """Restore selection to given indices."""
        self._link_list_view.restore_selection(indices)
    
    # Event handlers
    def _on_data_changed(self) -> None:
        """Handle data changes from the service."""
        selected_indices = self._get_selected_indices()
        self._refresh_view()
        self._restore_selection(selected_indices)
    
    def _on_profile_changed(self, profile_name: str) -> None:
        """Handle profile selection change."""
        if self._profile_service.switch_to_profile(profile_name):
            # Clear search and sort when switching profiles
            self._current_search_term = ""
            self._current_sort_column = None
            self._current_sort_reverse = False
            self._search_bar.clear_search()
            self._refresh_view()
    
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
        """Handle delete key press."""
        if not indices:
            return
        
        if len(indices) > 1:
            if not messagebox.askyesno("Confirm Deletion", 
                                     f"Are you sure you want to delete {len(indices)} selected link(s)?"):
                return
        
        self._profile_service.delete_links(indices)
    
    def _on_sort_requested(self, column: str, reverse: bool) -> None:
        """Handle sort request."""
        self._current_sort_column = column
        self._current_sort_reverse = reverse
        self._refresh_view()
    
    def _on_escape_pressed(self, event) -> None:
        """Handle escape key press based on which widget has focus."""
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
    
    # Action methods
    def _add_links(self) -> None:
        """Show add links dialog."""
        def add_links_callback(links_data: List[tuple]) -> None:
            for name, url in links_data:
                link = Link(name, url)
                self._profile_service.add_link(link)
        
        AddLinksDialog(self._root, add_links_callback)
    
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