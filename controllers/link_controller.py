import tkinter as tk
from tkinter import messagebox
from typing import List, Optional
from models.link import Link
from services.link_service import LinkService
from ui.components.link_list_view import LinkListView
from ui.components.search_bar import SearchBar
from ui.dialogs.edit_dialog import EditLinkDialog
from ui.dialogs.add_links_dialog import AddLinksDialog


class LinkController:
    """Controller for managing link operations and UI interactions."""
    
    def __init__(self, root: tk.Tk, link_service: LinkService):
        self._root = root
        self._link_service = link_service
        self._current_search_term = ""
        self._current_sort_column: Optional[str] = None
        self._current_sort_reverse = False
        
        # UI components
        self._search_bar: Optional[SearchBar] = None
        self._link_list_view: Optional[LinkListView] = None
        
        # Register as observer
        self._link_service.add_observer(self._on_data_changed)
        
        self._create_ui()
        self._setup_callbacks()
        self._refresh_view()
    
    def _create_ui(self) -> None:
        """Create the user interface."""
        # Main container
        container = tk.Frame(self._root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
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
        # Search bar callbacks
        self._search_bar.set_search_change_callback(self._on_search_changed)
        self._search_bar.set_clear_callback(self._on_search_cleared)
        
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
        else:
            # Windows/Linux shortcuts (using Ctrl key)
            self._root.bind("<Control-d>", lambda e: self._toggle_favorite())
            self._root.bind("<Control-e>", lambda e: self._toggle_read_status())
            self._root.bind("<Control-r>", lambda e: self._open_random())
        
        # Platform-independent shortcuts
        self._root.bind("<Return>", lambda e: self._edit_link())
    
    def _refresh_view(self) -> None:
        """Refresh the view with current data."""
        all_links = self._link_service.get_all_links()
        
        # Apply search filter
        if self._current_search_term:
            filtered_links = self._link_service.search_links(self._current_search_term)
        else:
            filtered_links = all_links
        
        # Apply sorting
        if self._current_sort_column:
            filtered_links = self._link_service.sort_links(
                filtered_links, self._current_sort_column, self._current_sort_reverse
            )
        
        # Update UI components
        self._link_list_view.set_links(all_links, filtered_links)
        self._link_list_view.set_sort_column(self._current_sort_column, self._current_sort_reverse)
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
        selected_indices = self._get_selected_indices()
        self._refresh_view()
        self._restore_selection(selected_indices)
    
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
            self._link_service.open_links_batch(indices)
    
    def _on_delete_key_pressed(self, indices: List[int]) -> None:
        """Handle delete key press."""
        if not indices:
            return
        
        if len(indices) > 1:
            if not messagebox.askyesno("Confirm Deletion", 
                                     f"Are you sure you want to delete {len(indices)} selected link(s)?"):
                return
        
        self._link_service.delete_links_batch(indices)
    
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
        AddLinksDialog(self._root, self._link_service.add_links_batch)
    
    def _edit_link(self) -> None:
        """Show edit link dialog."""
        indices = self._get_selected_indices()
        if not indices:
            return
        if len(indices) > 1:
            messagebox.showinfo("Info", "Please select only one item to edit.")
            return
        
        link_id = indices[0]
        link = self._link_service.get_link(link_id)
        if not link:
            return
        
        def on_save(updated_link: Link) -> None:
            self._link_service.update_link(
                link_id, updated_link.name, updated_link.url, updated_link.favorite,
                updated_link.date_added, updated_link.last_opened
            )
        
        EditLinkDialog(self._root, link, on_save)
    
    def _toggle_favorite(self) -> None:
        """Toggle favorite status of selected links."""
        indices = self._get_selected_indices()
        if indices:
            self._link_service.toggle_favorites_batch(indices)
    
    def _toggle_read_status(self) -> None:
        """Toggle read status of selected links."""
        indices = self._get_selected_indices()
        if indices:
            self._link_service.toggle_read_status(indices)
    
    def _open_random(self) -> None:
        """Open a random link and select it in the UI."""
        link_index = self._link_service.open_random_link()
        if link_index is not None:
            self._link_list_view.select_and_scroll_to(link_index)
        else:
            messagebox.showinfo("Info", "No links available.")
    
    def _open_random_unread(self) -> None:
        """Open a random unread link and select it in the UI."""
        link_index = self._link_service.open_random_unread_link()
        if link_index is not None:
            self._link_list_view.select_and_scroll_to(link_index)
        else:
            messagebox.showinfo("Info", "No unread links available.")