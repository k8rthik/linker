import sys
import tkinter as tk
from tkinter import ttk
from typing import List, Callable, Optional
from models.link import Link
from utils.date_formatter import DateFormatter


class LinkListView:
    """Component for displaying and managing the link list."""
    
    def __init__(self, parent: tk.Widget):
        self._parent = parent
        self._links: List[Link] = []
        self._filtered_links: List[Link] = []
        self._sort_column: Optional[str] = None
        self._sort_reverse: bool = False
        
        # Callbacks
        self._on_double_click: Optional[Callable[[List[int]], None]] = None
        self._on_delete_key: Optional[Callable[[List[int]], None]] = None
        self._on_sort: Optional[Callable[[str, bool], None]] = None
        self._on_selection_changed: Optional[Callable[[List[int]], None]] = None
        
        self._create_components()
    
    def _create_components(self) -> None:
        """Create the treeview and scrollbar components."""
        # Create Treeview with columns
        columns = ("name", "url", "date_added", "last_opened", "tags")
        self._tree = ttk.Treeview(self._parent, columns=columns, show="tree headings", selectmode="extended")
        
        # Configure columns
        self._tree.heading("#0", text="Fav")
        self._tree.column("#0", width=40, minwidth=40)
        
        self._tree.heading("name", text="Name")
        self._tree.column("name", width=200, minwidth=150)
        
        self._tree.heading("url", text="URL")
        self._tree.column("url", width=300, minwidth=200)
        
        self._tree.heading("date_added", text="Date Added")
        self._tree.column("date_added", width=130, minwidth=130)
        
        self._tree.heading("last_opened", text="Last Opened")
        self._tree.column("last_opened", width=130, minwidth=130)
        
        self._tree.heading("tags", text="Tags")
        self._tree.column("tags", width=150, minwidth=100)
        
        # Bind column header clicks for sorting
        self._tree.heading("#0", command=lambda: self._on_column_clicked("favorite"))
        self._tree.heading("name", command=lambda: self._on_column_clicked("name"))
        self._tree.heading("url", command=lambda: self._on_column_clicked("url"))
        self._tree.heading("date_added", command=lambda: self._on_column_clicked("date_added"))
        self._tree.heading("last_opened", command=lambda: self._on_column_clicked("last_opened"))
        self._tree.heading("tags", command=lambda: self._on_column_clicked("tags"))
        
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        self._scrollbar = ttk.Scrollbar(self._parent, orient=tk.VERTICAL, command=self._tree.yview)
        self._scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self._tree.config(yscrollcommand=self._scrollbar.set)
        
        # Bind events
        self._tree.bind("<Double-Button-1>", self._on_double_click_event)
        self._tree.bind("<BackSpace>", self._on_delete_key_event)
        self._tree.bind("<<TreeviewSelect>>", self._on_selection_changed_event)
    
    def set_links(self, links: List[Link], filtered_links: List[Link]) -> None:
        """Set the links to display."""
        self._links = links
        self._filtered_links = filtered_links
        self._refresh_display()
    
    def _refresh_display(self) -> None:
        """Refresh the display with current filtered links."""
        # Clear existing items
        for item in self._tree.get_children():
            self._tree.delete(item)
        
        # Add filtered links
        for link in self._filtered_links:
            favorite_icon = "★" if link.favorite else ""
            name = link.name
            url = link.url
            date_added = DateFormatter.format_datetime(link.date_added)
            last_opened = DateFormatter.format_datetime(link.last_opened)
            tags_display = ", ".join(sorted(link.tags)) if link.tags else ""
            
            # Use the original index from self._links for proper mapping
            original_index = self._links.index(link) if link in self._links else -1
            if original_index >= 0:
                self._tree.insert("", "end", iid=str(original_index), text=favorite_icon, 
                               values=(name, url, date_added, last_opened, tags_display))
    
    def get_selected_indices(self) -> List[int]:
        """Get the indices of selected items."""
        selected_items = self._tree.selection()
        return [int(item) for item in selected_items if item.isdigit()]
    
    def restore_selection(self, indices: List[int]) -> None:
        """Restore selection to the given indices."""
        self._tree.selection_clear()
        for idx in indices:
            if idx < len(self._links):
                item_id = str(idx)
                if self._tree.exists(item_id):
                    self._tree.selection_add(item_id)
    
    def select_and_scroll_to(self, index: int) -> None:
        """Select and scroll to a specific link."""
        if index < len(self._links):
            item_id = str(index)
            if self._tree.exists(item_id):
                self._tree.selection_set(item_id)
                self._tree.see(item_id)
    
    def clear_selection(self) -> None:
        """Clear all selections."""
        self._tree.selection_clear()
    
    def set_sort_column(self, column: Optional[str], reverse: bool = False) -> None:
        """Set the current sort column and update headers."""
        self._sort_column = column
        self._sort_reverse = reverse
        self._update_column_headers()
    
    def _update_column_headers(self) -> None:
        """Update column headers to show sort direction."""
        # Reset all headers
        self._tree.heading("#0", text="Fav")
        self._tree.heading("name", text="Name")
        self._tree.heading("url", text="URL")
        self._tree.heading("date_added", text="Date Added")
        self._tree.heading("last_opened", text="Last Opened")
        self._tree.heading("tags", text="Tags")
        
        # Add sort indicator to current sort column
        if self._sort_column:
            indicator = " ↓" if self._sort_reverse else " ↑"
            if self._sort_column == "favorite":
                self._tree.heading("#0", text="Fav" + indicator)
            elif self._sort_column == "name":
                self._tree.heading("name", text="Name" + indicator)
            elif self._sort_column == "url":
                self._tree.heading("url", text="URL" + indicator)
            elif self._sort_column == "date_added":
                self._tree.heading("date_added", text="Date Added" + indicator)
            elif self._sort_column == "last_opened":
                self._tree.heading("last_opened", text="Last Opened" + indicator)
            elif self._sort_column == "tags":
                self._tree.heading("tags", text="Tags" + indicator)
    
    def bind_keyboard_shortcuts(self, root: tk.Tk) -> None:
        """Bind keyboard shortcuts."""
        # Bind Escape key to clear selection
        root.bind("<Escape>", lambda e: self.clear_selection())
    
    def focus(self) -> None:
        """Give focus to the tree view."""
        self._tree.focus_set()
    
    # Event handlers
    def _on_double_click_event(self, event) -> None:
        """Handle double-click event."""
        if self._on_double_click:
            indices = self.get_selected_indices()
            if indices:
                self._on_double_click(indices)
    
    def _on_delete_key_event(self, event) -> None:
        """Handle delete key event."""
        if self._on_delete_key:
            indices = self.get_selected_indices()
            if indices:
                self._on_delete_key(indices)
    
    def _on_column_clicked(self, column: str) -> None:
        """Handle column header click for sorting."""
        if self._on_sort:
            # Toggle sort direction if clicking the same column
            reverse = False
            if self._sort_column == column:
                reverse = not self._sort_reverse
            self._on_sort(column, reverse)
    
    def _on_selection_changed_event(self, event) -> None:
        """Handle selection change event."""
        if self._on_selection_changed:
            indices = self.get_selected_indices()
            self._on_selection_changed(indices)
    
    # Callback setters
    def set_double_click_callback(self, callback: Callable[[List[int]], None]) -> None:
        """Set callback for double-click events."""
        self._on_double_click = callback
    
    def set_delete_key_callback(self, callback: Callable[[List[int]], None]) -> None:
        """Set callback for delete key events."""
        self._on_delete_key = callback
    
    def set_sort_callback(self, callback: Callable[[str, bool], None]) -> None:
        """Set callback for sort events."""
        self._on_sort = callback
    
    def set_selection_changed_callback(self, callback: Callable[[List[int]], None]) -> None:
        """Set callback for selection change events."""
        self._on_selection_changed = callback 