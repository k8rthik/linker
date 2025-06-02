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
        self._on_space_key: Optional[Callable[[], None]] = None
        self._on_sort: Optional[Callable[[str, bool], None]] = None
        
        self._create_components()
    
    def _create_components(self) -> None:
        """Create the treeview and scrollbar components."""
        # Create Treeview with columns
        columns = ("name", "url", "date_added", "last_opened")
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
        
        # Bind column header clicks for sorting
        self._tree.heading("#0", command=lambda: self._on_column_clicked("favorite"))
        self._tree.heading("name", command=lambda: self._on_column_clicked("name"))
        self._tree.heading("url", command=lambda: self._on_column_clicked("url"))
        self._tree.heading("date_added", command=lambda: self._on_column_clicked("date_added"))
        self._tree.heading("last_opened", command=lambda: self._on_column_clicked("last_opened"))
        
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        self._scrollbar = ttk.Scrollbar(self._parent, orient=tk.VERTICAL, command=self._tree.yview)
        self._scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self._tree.config(yscrollcommand=self._scrollbar.set)
        
        # Bind events
        self._tree.bind("<Double-Button-1>", self._on_double_click_event)
        self._tree.bind("<BackSpace>", self._on_delete_key_event)
        self._tree.bind("<KeyPress-space>", self._on_space_key_event)
        
        # Bind arrow key navigation
        self._tree.bind("<Up>", self._on_arrow_up)
        self._tree.bind("<Down>", self._on_arrow_down)
        self._tree.bind("<Left>", self._on_arrow_left)
        self._tree.bind("<Right>", self._on_arrow_right)
        self._tree.bind("<Home>", self._on_home_key)
        self._tree.bind("<End>", self._on_end_key)
        self._tree.bind("<Prior>", self._on_page_up)  # Page Up
        self._tree.bind("<Next>", self._on_page_down)  # Page Down
    
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
            
            # Use the original index from self._links for proper mapping
            original_index = self._links.index(link) if link in self._links else -1
            if original_index >= 0:
                self._tree.insert("", "end", iid=str(original_index), text=favorite_icon, 
                               values=(name, url, date_added, last_opened))
    
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
    
    def has_focus(self) -> bool:
        """Check if the tree view has focus."""
        return self._tree == self._tree.focus_get()

    def bind_keyboard_shortcuts(self, root: tk.Tk) -> None:
        """Bind keyboard shortcuts."""
        # Note: Escape key is handled by the controller based on focus
        # Arrow keys are handled directly by the tree widget
        pass
    
    def focus(self) -> None:
        """Give focus to the tree view."""
        self._tree.focus_set()
        # Only select the first item if there are no items at all and this is the initial focus
        # This prevents the bug where returning from browser causes unwanted selection
        # if not self._tree.selection() and self._tree.get_children():
        #     first_item = self._tree.get_children()[0]
        #     self._tree.selection_set(first_item)
        #     self._tree.focus(first_item)
    
    def get_current_item(self) -> Optional[str]:
        """Get the currently focused item."""
        return self._tree.focus()
    
    def get_visible_items(self) -> List[str]:
        """Get all visible items in the tree."""
        return list(self._tree.get_children())
    
    def select_item(self, item_id: str, extend: bool = False) -> None:
        """Select a specific item."""
        if self._tree.exists(item_id):
            if extend:
                self._tree.selection_add(item_id)
            else:
                # Clear all selections and select only this item
                self._tree.selection_set(item_id)
            self._tree.focus(item_id)
            self._tree.see(item_id)
    
    def navigate_to_item(self, direction: str) -> None:
        """Navigate to an item in the specified direction."""
        current = self._tree.focus()
        items = self.get_visible_items()
        
        if not items:
            return
        
        if not current or current not in items:
            # No current selection, select first item
            self.select_item(items[0])
            return
        
        current_index = items.index(current)
        target_item = None
        
        if direction == "up" and current_index > 0:
            target_item = items[current_index - 1]
        elif direction == "down" and current_index < len(items) - 1:
            target_item = items[current_index + 1]
        elif direction == "home":
            target_item = items[0]
        elif direction == "end":
            target_item = items[-1]
        elif direction == "page_up":
            # Move up by ~10 items or to the beginning
            new_index = max(0, current_index - 10)
            target_item = items[new_index]
        elif direction == "page_down":
            # Move down by ~10 items or to the end
            new_index = min(len(items) - 1, current_index + 10)
            target_item = items[new_index]
        
        if target_item:
            self.select_item(target_item)
    
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
    
    def _on_space_key_event(self, event) -> None:
        """Handle space key event."""
        if self._on_space_key:
            self._on_space_key()
            return "break"  # Prevent default behavior
    
    def _on_column_clicked(self, column: str) -> None:
        """Handle column header click for sorting."""
        if self._on_sort:
            # Toggle sort direction if clicking the same column
            reverse = False
            if self._sort_column == column:
                reverse = not self._sort_reverse
            self._on_sort(column, reverse)
    
    # Arrow key event handlers
    def _on_arrow_up(self, event) -> str:
        """Handle up arrow key."""
        self.navigate_to_item("up")
        return "break"  # Prevent default behavior
    
    def _on_arrow_down(self, event) -> str:
        """Handle down arrow key."""
        self.navigate_to_item("down")
        return "break"  # Prevent default behavior
    
    def _on_arrow_left(self, event) -> str:
        """Handle left arrow key."""
        # Prevent default horizontal navigation
        return "break"
    
    def _on_arrow_right(self, event) -> str:
        """Handle right arrow key."""
        # Prevent default horizontal navigation
        return "break"
    
    def _on_home_key(self, event) -> str:
        """Handle Home key."""
        self.navigate_to_item("home")
        return "break"
    
    def _on_end_key(self, event) -> str:
        """Handle End key."""
        self.navigate_to_item("end")
        return "break"
    
    def _on_page_up(self, event) -> str:
        """Handle Page Up key."""
        self.navigate_to_item("page_up")
        return "break"
    
    def _on_page_down(self, event) -> str:
        """Handle Page Down key."""
        self.navigate_to_item("page_down")
        return "break"
    
    # Callback setters
    def set_double_click_callback(self, callback: Callable[[List[int]], None]) -> None:
        """Set callback for double-click events."""
        self._on_double_click = callback
    
    def set_delete_key_callback(self, callback: Callable[[List[int]], None]) -> None:
        """Set callback for delete key events."""
        self._on_delete_key = callback
    
    def set_space_key_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for space key events."""
        self._on_space_key = callback
    
    def set_sort_callback(self, callback: Callable[[str, bool], None]) -> None:
        """Set callback for sort events."""
        self._on_sort = callback 