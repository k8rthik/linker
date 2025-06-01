import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Callable, Optional, Set


class TagManager:
    """Component for managing tags on selected links."""
    
    def __init__(self, parent: tk.Widget):
        self._parent = parent
        self._on_tags_changed: Optional[Callable[[List[int], str, str], None]] = None
        self._all_tags: List[str] = []
        self._selected_link_ids: List[int] = []
        self._current_tags: Set[str] = set()
        
        self._create_ui()
    
    def _create_ui(self) -> None:
        """Create the tag manager UI."""
        # Main frame
        self._frame = tk.Frame(self._parent)
        self._frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Title
        title_label = tk.Label(self._frame, text="Tags", font=("Arial", 10, "bold"))
        title_label.pack(anchor=tk.W)
        
        # Tag input frame
        input_frame = tk.Frame(self._frame)
        input_frame.pack(fill=tk.X, pady=(2, 5))
        
        # Tag entry with autocomplete
        self._tag_var = tk.StringVar()
        self._tag_entry = ttk.Combobox(
            input_frame, 
            textvariable=self._tag_var,
            width=20,
            state="normal"
        )
        self._tag_entry.pack(side=tk.LEFT, padx=(0, 5))
        self._tag_entry.bind('<Return>', self._on_add_tag)
        self._tag_entry.bind('<KeyRelease>', self._on_tag_input_changed)
        
        # Add tag button
        self._add_btn = tk.Button(
            input_frame,
            text="Add",
            command=self._on_add_tag,
            width=8
        )
        self._add_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Quick action buttons
        self._clear_btn = tk.Button(
            input_frame,
            text="Clear All",
            command=self._on_clear_all_tags,
            width=8
        )
        self._clear_btn.pack(side=tk.LEFT)
        
        # Current tags frame
        tags_frame = tk.Frame(self._frame)
        tags_frame.pack(fill=tk.BOTH, expand=True)
        
        # Current tags label
        current_label = tk.Label(tags_frame, text="Current tags:", font=("Arial", 9))
        current_label.pack(anchor=tk.W)
        
        # Tags display frame with scrollbar
        display_frame = tk.Frame(tags_frame)
        display_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable frame for tags
        self._tags_canvas = tk.Canvas(display_frame, height=60)
        self._tags_scrollbar = ttk.Scrollbar(display_frame, orient=tk.VERTICAL, command=self._tags_canvas.yview)
        self._tags_scroll_frame = tk.Frame(self._tags_canvas)
        
        self._tags_scroll_frame.bind(
            "<Configure>",
            lambda e: self._tags_canvas.configure(scrollregion=self._tags_canvas.bbox("all"))
        )
        
        self._tags_canvas.create_window((0, 0), window=self._tags_scroll_frame, anchor="nw")
        self._tags_canvas.configure(yscrollcommand=self._tags_scrollbar.set)
        
        self._tags_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._tags_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind mouse wheel to canvas
        self._tags_canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # Status label
        self._status_label = tk.Label(self._frame, text="No links selected", font=("Arial", 8), fg="gray")
        self._status_label.pack(anchor=tk.W, pady=(2, 0))
        
        self._update_ui_state()
    
    def set_tags_changed_callback(self, callback: Callable[[List[int], str, str], None]) -> None:
        """Set callback for when tags are changed.
        
        Args:
            callback: Function that takes (link_ids, action, tag) where action is 'add', 'remove', or 'clear'
        """
        self._on_tags_changed = callback
    
    def set_all_tags(self, tags: List[str]) -> None:
        """Set the list of all available tags for autocomplete."""
        self._all_tags = tags
        self._tag_entry['values'] = tags
    
    def set_selected_links(self, link_ids: List[int], current_tags: Set[str]) -> None:
        """Set currently selected links and their tags."""
        self._selected_link_ids = link_ids
        self._current_tags = current_tags
        self._update_ui_state()
        self._update_tags_display()
    
    def _update_ui_state(self) -> None:
        """Update UI state based on selection."""
        has_selection = len(self._selected_link_ids) > 0
        
        # Enable/disable controls
        state = tk.NORMAL if has_selection else tk.DISABLED
        self._tag_entry.configure(state=state)
        self._add_btn.configure(state=state)
        self._clear_btn.configure(state=state)
        
        # Update status
        if has_selection:
            count = len(self._selected_link_ids)
            self._status_label.configure(
                text=f"{count} link{'s' if count != 1 else ''} selected",
                fg="black"
            )
        else:
            self._status_label.configure(text="No links selected", fg="gray")
    
    def _update_tags_display(self) -> None:
        """Update the display of current tags."""
        # Clear existing tag widgets
        for widget in self._tags_scroll_frame.winfo_children():
            widget.destroy()
        
        if not self._current_tags:
            no_tags_label = tk.Label(
                self._tags_scroll_frame, 
                text="No tags", 
                font=("Arial", 8), 
                fg="gray"
            )
            no_tags_label.pack(anchor=tk.W, padx=5, pady=2)
            return
        
        # Create tag widgets
        for i, tag in enumerate(sorted(self._current_tags)):
            self._create_tag_widget(tag, i)
        
        # Update scroll region
        self._tags_scroll_frame.update_idletasks()
        self._tags_canvas.configure(scrollregion=self._tags_canvas.bbox("all"))
    
    def _create_tag_widget(self, tag: str, index: int) -> None:
        """Create a widget for displaying and removing a tag."""
        tag_frame = tk.Frame(self._tags_scroll_frame, relief=tk.RAISED, bd=1)
        tag_frame.pack(fill=tk.X, padx=2, pady=1)
        
        # Tag label
        tag_label = tk.Label(
            tag_frame, 
            text=tag, 
            font=("Arial", 8),
            bg="#e1f5fe",
            padx=8,
            pady=2
        )
        tag_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Remove button
        remove_btn = tk.Button(
            tag_frame,
            text="×",
            font=("Arial", 8, "bold"),
            fg="red",
            bd=0,
            padx=4,
            pady=0,
            command=lambda t=tag: self._on_remove_tag(t)
        )
        remove_btn.pack(side=tk.RIGHT)
    
    def _on_tag_input_changed(self, event) -> None:
        """Handle changes in tag input for autocomplete."""
        current_text = self._tag_var.get()
        if len(current_text) >= 1:
            # Filter tags that start with current text
            matching_tags = [
                tag for tag in self._all_tags 
                if tag.lower().startswith(current_text.lower())
            ]
            self._tag_entry['values'] = matching_tags
    
    def _on_add_tag(self, event=None) -> None:
        """Handle adding a new tag."""
        tag = self._tag_var.get().strip()
        if not tag:
            return
        
        if tag in self._current_tags:
            messagebox.showinfo("Info", f"Tag '{tag}' already exists on selected links.")
            return
        
        # Add tag and notify
        if self._on_tags_changed:
            self._on_tags_changed(self._selected_link_ids, "add", tag)
        
        # Clear input
        self._tag_var.set("")
        self._tag_entry.focus()
    
    def _on_remove_tag(self, tag: str) -> None:
        """Handle removing a tag."""
        if self._on_tags_changed:
            self._on_tags_changed(self._selected_link_ids, "remove", tag)
    
    def _on_clear_all_tags(self) -> None:
        """Handle clearing all tags."""
        if not self._current_tags:
            return
        
        if messagebox.askyesno("Confirm", "Remove all tags from selected links?"):
            if self._on_tags_changed:
                self._on_tags_changed(self._selected_link_ids, "clear", "")
    
    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel scrolling."""
        self._tags_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def get_frame(self) -> tk.Frame:
        """Get the main frame widget."""
        return self._frame 