import tkinter as tk
from tkinter import ttk
from typing import List, Callable, Optional, Set


class TagFilter:
    """Component for filtering links by tags."""
    
    def __init__(self, parent: tk.Widget):
        self._parent = parent
        self._on_filter_changed: Optional[Callable[[List[str], bool], None]] = None
        self._all_tags: List[str] = []
        self._selected_tags: Set[str] = set()
        self._match_all = True
        
        self._create_ui()
    
    def _create_ui(self) -> None:
        """Create the tag filter UI."""
        # Main frame
        self._frame = tk.LabelFrame(self._parent, text="Filter by Tags", font=("Arial", 9, "bold"))
        self._frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Control frame
        control_frame = tk.Frame(self._frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Match mode frame
        mode_frame = tk.Frame(control_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(mode_frame, text="Match:", font=("Arial", 8)).pack(side=tk.LEFT)
        
        self._match_var = tk.StringVar(value="all")
        tk.Radiobutton(
            mode_frame,
            text="All tags",
            variable=self._match_var,
            value="all",
            font=("Arial", 8),
            command=self._on_match_mode_changed
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        tk.Radiobutton(
            mode_frame,
            text="Any tag",
            variable=self._match_var,
            value="any",
            font=("Arial", 8),
            command=self._on_match_mode_changed
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # Clear button
        tk.Button(
            mode_frame,
            text="Clear",
            command=self._clear_selection,
            font=("Arial", 8),
            width=8
        ).pack(side=tk.RIGHT)
        
        # Tags list frame with scrollbar
        list_frame = tk.Frame(self._frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # Create listbox with scrollbar
        self._listbox = tk.Listbox(
            list_frame,
            selectmode=tk.MULTIPLE,
            font=("Arial", 8),
            height=8
        )
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scrollbar.set)
        
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection events
        self._listbox.bind('<<ListboxSelect>>', self._on_selection_changed)
        
        # Status label
        self._status_label = tk.Label(
            self._frame,
            text="No tags available",
            font=("Arial", 8),
            fg="gray"
        )
        self._status_label.pack(anchor=tk.W, padx=5, pady=(0, 5))
        
        self._update_status()
    
    def set_filter_changed_callback(self, callback: Callable[[List[str], bool], None]) -> None:
        """Set callback for when filter changes.
        
        Args:
            callback: Function that takes (selected_tags, match_all) 
        """
        self._on_filter_changed = callback
    
    def set_available_tags(self, tags: List[str], tag_counts: dict = None) -> None:
        """Set the list of available tags.
        
        Args:
            tags: List of tag names
            tag_counts: Optional dictionary mapping tag names to usage counts
        """
        self._all_tags = tags
        self._update_tags_list(tag_counts)
        self._update_status()
    
    def get_selected_tags(self) -> List[str]:
        """Get currently selected tags."""
        return list(self._selected_tags)
    
    def get_match_all(self) -> bool:
        """Get whether to match all tags or any tag."""
        return self._match_all
    
    def clear_filter(self) -> None:
        """Clear all tag selections."""
        self._clear_selection()
    
    def _update_tags_list(self, tag_counts: dict = None) -> None:
        """Update the tags listbox."""
        self._listbox.delete(0, tk.END)
        
        for tag in self._all_tags:
            display_text = tag
            if tag_counts and tag in tag_counts:
                count = tag_counts[tag]
                display_text = f"{tag} ({count})"
            
            self._listbox.insert(tk.END, display_text)
            
            # Restore selection if tag was previously selected
            if tag in self._selected_tags:
                self._listbox.selection_set(tk.END)
    
    def _update_status(self) -> None:
        """Update the status label."""
        if not self._all_tags:
            self._status_label.configure(text="No tags available", fg="gray")
        elif not self._selected_tags:
            self._status_label.configure(
                text=f"{len(self._all_tags)} tags available",
                fg="gray"
            )
        else:
            count = len(self._selected_tags)
            mode = "all" if self._match_all else "any"
            self._status_label.configure(
                text=f"Filtering by {count} tag{'s' if count != 1 else ''} (match {mode})",
                fg="blue"
            )
    
    def _on_selection_changed(self, event) -> None:
        """Handle listbox selection changes."""
        selected_indices = self._listbox.curselection()
        self._selected_tags = {
            self._all_tags[i] for i in selected_indices
            if i < len(self._all_tags)
        }
        
        self._update_status()
        self._notify_filter_changed()
    
    def _on_match_mode_changed(self) -> None:
        """Handle match mode radio button changes."""
        self._match_all = self._match_var.get() == "all"
        self._update_status()
        if self._selected_tags:  # Only notify if we have selected tags
            self._notify_filter_changed()
    
    def _clear_selection(self) -> None:
        """Clear all tag selections."""
        self._listbox.selection_clear(0, tk.END)
        self._selected_tags.clear()
        self._update_status()
        self._notify_filter_changed()
    
    def _notify_filter_changed(self) -> None:
        """Notify callback about filter changes."""
        if self._on_filter_changed:
            self._on_filter_changed(list(self._selected_tags), self._match_all)
    
    def get_frame(self) -> tk.LabelFrame:
        """Get the main frame widget."""
        return self._frame 