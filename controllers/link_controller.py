import tkinter as tk
from tkinter import messagebox
from typing import List, Optional, Set
from models.link import Link
from services.link_service import LinkService
from ui.components.link_list_view import LinkListView
from ui.components.search_bar import SearchBar
from ui.components.tag_manager import TagManager
from ui.components.tag_filter import TagFilter
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
        self._active_tag_filter: List[str] = []
        self._tag_match_all = True
        
        # UI components
        self._search_bar: Optional[SearchBar] = None
        self._link_list_view: Optional[LinkListView] = None
        self._tag_manager: Optional[TagManager] = None
        self._tag_filter: Optional[TagFilter] = None
        
        # Register as observer
        self._link_service.add_observer(self._on_data_changed)
        
        self._create_ui()
        self._setup_callbacks()
        self._refresh_view()
    
    def _create_ui(self) -> None:
        """Create the user interface."""
        # Main container
        main_container = tk.Frame(self._root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create top panel with search
        top_panel = tk.Frame(main_container)
        top_panel.pack(fill=tk.X, pady=(0, 10))
        
        # Search bar
        self._search_bar = SearchBar(top_panel)
        
        # Create main content area
        content_frame = tk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for tags
        left_panel = tk.Frame(content_frame, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Tag manager in left panel
        self._tag_manager = TagManager(left_panel)
        
        # Tag filter in left panel
        self._tag_filter = TagFilter(left_panel)
        
        # Right panel for links list
        right_panel = tk.Frame(content_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Link list view
        self._link_list_view = LinkListView(right_panel)
        
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
        self._link_list_view.set_sort_callback(self._on_sort_requested)
        self._link_list_view.set_selection_changed_callback(self._on_link_selection_changed)
        
        # Tag manager callbacks
        self._tag_manager.set_tags_changed_callback(self._on_tags_changed)
        
        # Tag filter callbacks
        self._tag_filter.set_filter_changed_callback(self._on_tag_filter_changed)
    
    def _setup_keyboard_shortcuts(self) -> None:
        """Setup global keyboard shortcuts."""
        self._search_bar.bind_keyboard_shortcuts(self._root)
        self._link_list_view.bind_keyboard_shortcuts(self._root)
        
        # Escape key handling
        self._root.bind("<Escape>", self._on_escape_pressed)
    
    def _refresh_view(self) -> None:
        """Refresh the view with current data."""
        all_links = self._link_service.get_all_links()
        
        # Apply search filter
        if self._current_search_term:
            filtered_links = self._link_service.search_links_with_tags(self._current_search_term)
        else:
            filtered_links = all_links
        
        # Apply tag filter
        if self._active_tag_filter:
            filtered_links = [
                link for link in filtered_links
                if self._matches_tag_filter(link)
            ]
        
        # Apply sorting
        if self._current_sort_column:
            filtered_links = self._link_service.sort_links(
                filtered_links, self._current_sort_column, self._current_sort_reverse
            )
        
        # Update UI components
        self._link_list_view.set_links(all_links, filtered_links)
        self._link_list_view.set_sort_column(self._current_sort_column, self._current_sort_reverse)
        self._search_bar.set_result_count(len(filtered_links), len(all_links))
        
        # Update tag components
        all_tags = self._link_service.get_all_tags()
        tag_counts = self._link_service.get_tag_usage_count()
        
        self._tag_manager.set_all_tags(all_tags)
        self._tag_filter.set_available_tags(all_tags, tag_counts)
        
        # Update tag manager with current selection
        self._update_tag_manager_selection()
    
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
        """Handle escape key press."""
        if self._search_bar.get_search_term():
            self._search_bar.clear_search()
        else:
            self._link_list_view.clear_selection()
    
    # New event handlers for tags
    def _on_link_selection_changed(self, indices: List[int]) -> None:
        """Handle link selection changes to update tag manager."""
        self._update_tag_manager_selection()
    
    def _on_tags_changed(self, link_ids: List[int], action: str, tag: str) -> None:
        """Handle tag operations on selected links."""
        if action == "add":
            self._link_service.add_tag_to_links(link_ids, tag)
        elif action == "remove":
            self._link_service.remove_tag_from_links(link_ids, tag)
        elif action == "clear":
            self._link_service.clear_tags_from_links(link_ids)
    
    def _on_tag_filter_changed(self, selected_tags: List[str], match_all: bool) -> None:
        """Handle tag filter changes."""
        self._active_tag_filter = selected_tags
        self._tag_match_all = match_all
        self._refresh_view()
    
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
        
        # Get all available tags for autocomplete
        all_tags = self._link_service.get_all_tags()
        
        def on_save(updated_link: Link) -> None:
            self._link_service.update_link_with_tags(
                link_id, updated_link.name, updated_link.url, updated_link.favorite,
                updated_link.tags, updated_link.date_added, updated_link.last_opened
            )
        
        EditLinkDialog(self._root, link, on_save, all_tags)
    
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
        """Open a random link."""
        success = self._link_service.open_random_link()
        if not success:
            messagebox.showinfo("Info", "No links available.")
    
    def _open_random_unread(self) -> None:
        """Open a random unread link."""
        success = self._link_service.open_random_unread_link()
        if not success:
            messagebox.showinfo("Info", "No unread links available.")
    
    def _matches_tag_filter(self, link: Link) -> bool:
        """Check if link matches current tag filter."""
        if not self._active_tag_filter:
            return True
        
        if self._tag_match_all:
            return all(link.has_tag(tag) for tag in self._active_tag_filter)
        else:
            return any(link.has_tag(tag) for tag in self._active_tag_filter)
    
    def _update_tag_manager_selection(self) -> None:
        """Update tag manager with current link selection."""
        selected_indices = self._get_selected_indices()
        
        if not selected_indices:
            self._tag_manager.set_selected_links([], set())
            return
        
        # Get common tags across all selected links
        common_tags = None
        for link_id in selected_indices:
            link = self._link_service.get_link(link_id)
            if link:
                if common_tags is None:
                    common_tags = link.tags.copy()
                else:
                    common_tags.intersection_update(link.tags)
        
        if common_tags is None:
            common_tags = set()
        
        self._tag_manager.set_selected_links(selected_indices, common_tags) 