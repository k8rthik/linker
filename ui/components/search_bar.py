import sys
import tkinter as tk
from typing import Callable, Optional, List


class SearchBar:
    """Component for search functionality with debounced search and tag filtering."""

    def __init__(self, parent: tk.Widget):
        self._parent = parent
        self._on_search_change: Optional[Callable[[str], None]] = None
        self._on_clear: Optional[Callable[[], None]] = None
        self._on_open_all: Optional[Callable[[], None]] = None
        self._on_filter_change: Optional[Callable[[], None]] = None
        self._debounce_timer: Optional[str] = None
        self._debounce_delay_ms = 150  # 150ms debounce delay
        self._active_tag_filters: List[str] = []
        self._tag_filter_pills: List[tk.Frame] = []
        self._create_components()
    
    def _create_components(self) -> None:
        """Create search bar components."""
        self._frame = tk.Frame(self._parent)
        self._frame.pack(fill=tk.X, pady=(0, 5))
        
        # Search label
        tk.Label(self._frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Search entry
        self._search_var = tk.StringVar()
        self._search_entry = tk.Entry(self._frame, textvariable=self._search_var, width=30)
        self._search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Bind search as user types
        self._search_var.trace_add('write', self._on_search_var_change)
        
        # Clear button
        self._clear_btn = tk.Button(self._frame, text="Clear", command=self._on_clear_clicked)
        self._clear_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Open All button
        self._open_all_btn = tk.Button(self._frame, text="Open All", command=self._on_open_all_clicked)
        self._open_all_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Result count label
        self._result_label = tk.Label(self._frame, text="")
        self._result_label.pack(side=tk.LEFT, padx=(10, 0))

        # Tag filter pills frame
        self._tag_filters_frame = tk.Frame(self._parent)
        self._tag_filters_frame.pack(fill=tk.X, pady=(0, 5))
    
    def get_search_term(self) -> str:
        """Get the current search term."""
        return self._search_var.get()
    
    def clear_search(self) -> None:
        """Clear the search term and cancel any pending debounced search."""
        # Cancel any pending search
        if self._debounce_timer:
            self._search_entry.after_cancel(self._debounce_timer)
            self._debounce_timer = None
        self._search_var.set("")
        self.focus()
    
    def set_result_count(self, filtered_count: int, total_count: int) -> None:
        """Update the result count display."""
        if self.get_search_term().strip():
            self._result_label.config(text=f"Showing {filtered_count} of {total_count} links")
        else:
            self._result_label.config(text="")
    
    def focus(self) -> None:
        """Focus the search entry and select all text."""
        self._search_entry.focus_set()
        self._search_entry.select_range(0, tk.END)
    
    def bind_keyboard_shortcuts(self, root: tk.Tk) -> None:
        """Bind keyboard shortcuts for search."""
        # Bind Ctrl+f/Cmd+f to focus search
        if sys.platform == "darwin":
            root.bind("<Command-f>", lambda e: self._focus_and_break(e))
        else:
            root.bind("<Control-f>", lambda e: self._focus_and_break(e))
    
    def _focus_and_break(self, event) -> str:
        """Focus search and prevent default behavior."""
        self.focus()
        return "break"
    
    def _on_search_var_change(self, *args) -> None:
        """Handle search variable change with debouncing."""
        # Cancel any pending search
        if self._debounce_timer:
            self._search_entry.after_cancel(self._debounce_timer)

        # Schedule a new search after the debounce delay
        self._debounce_timer = self._search_entry.after(
            self._debounce_delay_ms,
            self._execute_search
        )

    def _execute_search(self) -> None:
        """Execute the actual search after debounce delay."""
        self._debounce_timer = None
        if self._on_search_change:
            self._on_search_change(self.get_search_term())
    
    def _on_clear_clicked(self) -> None:
        """Handle clear button click."""
        self.clear_search()
        if self._on_clear:
            self._on_clear()
    
    def _on_open_all_clicked(self) -> None:
        """Handle open all button click."""
        if self._on_open_all:
            self._on_open_all()
    
    def set_search_change_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for search term changes."""
        self._on_search_change = callback
    
    def set_clear_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for clear action."""
        self._on_clear = callback
    
    def set_open_all_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for open all action."""
        self._on_open_all = callback

    def set_filter_change_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for filter changes (tag filters)."""
        self._on_filter_change = callback

    def has_focus(self) -> bool:
        """Check if the search entry has focus."""
        return self._search_entry == self._search_entry.focus_get()

    def set_search_term(self, term: str) -> None:
        """Set the search term without triggering the change callback."""
        # Temporarily disable the callback to avoid recursive calls
        original_callback = self._on_search_change
        self._on_search_change = None
        self._search_var.set(term)
        self._on_search_change = original_callback

    def add_tag_filter(self, tag: str) -> None:
        """Add a tag filter."""
        if tag and tag not in self._active_tag_filters:
            self._active_tag_filters.append(tag)
            self._refresh_tag_filter_pills()
            if self._on_filter_change:
                self._on_filter_change()

    def remove_tag_filter(self, tag: str) -> None:
        """Remove a tag filter."""
        if tag in self._active_tag_filters:
            self._active_tag_filters.remove(tag)
            self._refresh_tag_filter_pills()
            if self._on_filter_change:
                self._on_filter_change()

    def clear_tag_filters(self) -> None:
        """Clear all tag filters."""
        if self._active_tag_filters:
            self._active_tag_filters.clear()
            self._refresh_tag_filter_pills()
            if self._on_filter_change:
                self._on_filter_change()

    def get_active_tag_filters(self) -> List[str]:
        """Get list of active tag filters."""
        return self._active_tag_filters.copy()

    def _refresh_tag_filter_pills(self) -> None:
        """Refresh the display of tag filter pills."""
        # Clear existing pills
        for widget in self._tag_filters_frame.winfo_children():
            widget.destroy()
        self._tag_filter_pills.clear()

        if not self._active_tag_filters:
            return

        # Add label
        tk.Label(self._tag_filters_frame, text="Filters:", font=("TkDefaultFont", 8, "bold")).pack(
            side=tk.LEFT, padx=(0, 5))

        # Create pill for each tag filter
        for tag in self._active_tag_filters:
            pill_frame = tk.Frame(self._tag_filters_frame, bg="#4CAF50", relief=tk.RAISED, bd=1)
            pill_frame.pack(side=tk.LEFT, padx=2)

            tag_label = tk.Label(pill_frame, text=f"tag:{tag}", bg="#4CAF50", fg="white", padx=5, pady=2)
            tag_label.pack(side=tk.LEFT)

            remove_btn = tk.Button(
                pill_frame,
                text="×",
                bg="#4CAF50",
                fg="white",
                relief=tk.FLAT,
                padx=3,
                pady=0,
                command=lambda t=tag: self.remove_tag_filter(t)
            )
            remove_btn.pack(side=tk.LEFT)

            self._tag_filter_pills.append(pill_frame)

        # Add clear all button
        clear_all_btn = tk.Button(
            self._tag_filters_frame,
            text="Clear All",
            command=self.clear_tag_filters,
            relief=tk.FLAT,
            fg="blue"
        )
        clear_all_btn.pack(side=tk.LEFT, padx=(10, 0))