import sys
import tkinter as tk
from typing import Callable, Optional


class SearchBar:
    """Component for search functionality."""
    
    def __init__(self, parent: tk.Widget):
        self._parent = parent
        self._on_search_change: Optional[Callable[[str], None]] = None
        self._on_clear: Optional[Callable[[], None]] = None
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
        self._search_var.trace('w', self._on_search_var_change)
        
        # Clear button
        self._clear_btn = tk.Button(self._frame, text="Clear", command=self._on_clear_clicked)
        self._clear_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Result count label
        self._result_label = tk.Label(self._frame, text="")
        self._result_label.pack(side=tk.LEFT, padx=(10, 0))
    
    def get_search_term(self) -> str:
        """Get the current search term."""
        return self._search_var.get()
    
    def clear_search(self) -> None:
        """Clear the search term."""
        self._search_var.set("")
        self.focus()
    
    def set_result_count(self, filtered_count: int, total_count: int) -> None:
        """Update the result count display."""
        if self.get_search_term().strip():
            self._result_label.config(text=f"Showing {filtered_count} of {total_count} links")
        else:
            self._result_label.config(text=f"{total_count} links")
    
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
        """Handle search variable change."""
        if self._on_search_change:
            self._on_search_change(self.get_search_term())
    
    def _on_clear_clicked(self) -> None:
        """Handle clear button click."""
        self.clear_search()
        if self._on_clear:
            self._on_clear()
    
    def set_search_change_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for search term changes."""
        self._on_search_change = callback
    
    def set_clear_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for clear action."""
        self._on_clear = callback 