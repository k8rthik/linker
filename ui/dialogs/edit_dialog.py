import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable, List
from models.link import Link
from utils.date_formatter import DateFormatter


class EditLinkDialog:
    """Dialog for editing link properties with tag support."""

    def __init__(self, parent: tk.Tk, link: Link, on_save: Callable[[Link], None],
                 get_all_tags: Optional[Callable[[], List[str]]] = None):
        self._parent = parent
        self._original_link = link
        self._on_save = on_save
        self._get_all_tags = get_all_tags
        self._dialog: Optional[tk.Toplevel] = None
        self._current_tags = link.tags.copy()
        self._tag_pills: List[tk.Frame] = []
        self._create_dialog()
    
    def _create_dialog(self) -> None:
        """Create and show the edit dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Edit Link")
        self._dialog.geometry("500x500")
        self._dialog.resizable(True, True)
        
        # Main frame with padding
        main_frame = tk.Frame(self._dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create form fields
        self._create_form_fields(main_frame)
        
        # Create buttons
        self._create_buttons(main_frame)
        
        # Configure dialog
        self._configure_dialog()
    
    def _create_form_fields(self, parent: tk.Frame) -> None:
        """Create form input fields."""
        # Name field
        tk.Label(parent, text="Name:", font=("TkDefaultFont", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 5))
        self._name_var = tk.StringVar(value=self._original_link.name)
        self._name_entry = tk.Entry(parent, textvariable=self._name_var, width=60)
        self._name_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        # URL field
        tk.Label(parent, text="URL:", font=("TkDefaultFont", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=(0, 5))
        self._url_var = tk.StringVar(value=self._original_link.url)
        self._url_entry = tk.Entry(parent, textvariable=self._url_var, width=60)
        self._url_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        # Favorite checkbox
        self._favorite_var = tk.BooleanVar(value=self._original_link.favorite)
        favorite_check = tk.Checkbutton(parent, text="Favorite", variable=self._favorite_var,
                                       font=("TkDefaultFont", 9, "bold"))
        favorite_check.grid(row=4, column=0, sticky="w", pady=(0, 15))

        # Tags section
        tk.Label(parent, text="Tags:", font=("TkDefaultFont", 9, "bold")).grid(
            row=5, column=0, sticky="w", pady=(0, 5))

        # Tag input with autocomplete
        tag_input_frame = tk.Frame(parent)
        tag_input_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        self._tag_entry = tk.Entry(tag_input_frame, width=40)
        self._tag_entry.pack(side=tk.LEFT, padx=(0, 5))
        self._tag_entry.bind("<Return>", lambda e: self._add_tag_from_entry())
        self._tag_entry.bind("<KeyRelease>", self._on_tag_entry_change)

        add_tag_btn = tk.Button(tag_input_frame, text="Add Tag", command=self._add_tag_from_entry)
        add_tag_btn.pack(side=tk.LEFT)

        # Autocomplete listbox (initially hidden)
        self._autocomplete_frame = tk.Frame(parent)
        self._autocomplete_frame.grid(row=7, column=0, columnspan=2, sticky="ew")
        self._autocomplete_listbox = tk.Listbox(self._autocomplete_frame, height=5)
        self._autocomplete_listbox.pack(fill=tk.BOTH, expand=True)
        self._autocomplete_listbox.bind("<<ListboxSelect>>", self._on_autocomplete_select)
        self._autocomplete_frame.grid_remove()  # Hide initially

        # Tag pills container
        tk.Label(parent, text="Current tags:", font=("TkDefaultFont", 8), fg="gray").grid(
            row=8, column=0, sticky="w", pady=(5, 0))

        self._tags_container = tk.Frame(parent)
        self._tags_container.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(5, 15))
        self._refresh_tag_pills()

        # Date Added field
        tk.Label(parent, text="Date Added:", font=("TkDefaultFont", 9, "bold")).grid(
            row=10, column=0, sticky="w", pady=(0, 5))
        self._date_added_var = tk.StringVar(value=self._original_link.date_added)
        self._date_added_entry = tk.Entry(parent, textvariable=self._date_added_var, width=30)
        self._date_added_entry.grid(row=11, column=0, sticky="ew", pady=(0, 5))

        # Date format help text
        tk.Label(parent, text="Format: YYYY-MM-DDTHH:MM:SS (ISO format)",
                font=("TkDefaultFont", 8), fg="gray").grid(row=12, column=0, sticky="w", pady=(0, 15))

        # Last Opened field
        tk.Label(parent, text="Last Opened:", font=("TkDefaultFont", 9, "bold")).grid(
            row=13, column=0, sticky="w", pady=(0, 5))
        self._last_opened_var = tk.StringVar(value=self._original_link.last_opened or "")
        self._last_opened_entry = tk.Entry(parent, textvariable=self._last_opened_var, width=30)
        self._last_opened_entry.grid(row=14, column=0, sticky="ew", pady=(0, 5))

        # Last opened help text
        tk.Label(parent, text="Format: YYYY-MM-DDTHH:MM:SS (leave empty for 'never opened')",
                font=("TkDefaultFont", 8), fg="gray").grid(row=15, column=0, sticky="w", pady=(0, 20))

        # Configure grid weights
        parent.columnconfigure(0, weight=1)
    
    def _create_buttons(self, parent: tk.Frame) -> None:
        """Create dialog buttons."""
        btn_frame = tk.Frame(parent)
        btn_frame.grid(row=16, column=0, columnspan=2, pady=(10, 0))

        save_btn = tk.Button(btn_frame, text="Save (⌘⏎)", command=self._on_save_clicked, width=12)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))

        cancel_btn = tk.Button(btn_frame, text="Cancel", command=self._on_cancel_clicked, width=10)
        cancel_btn.pack(side=tk.LEFT)
    
    def _configure_dialog(self) -> None:
        """Configure dialog properties."""
        self._dialog.transient(self._parent)
        self._dialog.grab_set()
        self._name_entry.focus()
        self._name_entry.select_range(0, tk.END)
        
        # Bind keyboard shortcuts
        self._dialog.bind("<Control-Return>", lambda e: self._on_save_clicked())
        self._dialog.bind("<Command-Return>", lambda e: self._on_save_clicked())
        self._dialog.bind("<Escape>", lambda e: self._on_cancel_clicked())
        
        # Center the dialog
        self._dialog.update_idletasks()
        x = (self._dialog.winfo_screenwidth() // 2) - (self._dialog.winfo_width() // 2)
        y = (self._dialog.winfo_screenheight() // 2) - (self._dialog.winfo_height() // 2)
        self._dialog.geometry(f"+{x}+{y}")
    
    def _refresh_tag_pills(self) -> None:
        """Refresh the display of tag pills."""
        # Clear existing pills
        for widget in self._tags_container.winfo_children():
            widget.destroy()
        self._tag_pills.clear()

        # Create pill for each tag
        for tag in self._current_tags:
            pill_frame = tk.Frame(self._tags_container, bg="#e0e0e0", relief=tk.RAISED, bd=1)
            pill_frame.pack(side=tk.LEFT, padx=2, pady=2)

            tag_label = tk.Label(pill_frame, text=tag, bg="#e0e0e0", padx=5, pady=2)
            tag_label.pack(side=tk.LEFT)

            remove_btn = tk.Button(
                pill_frame,
                text="×",
                bg="#e0e0e0",
                fg="red",
                relief=tk.FLAT,
                padx=3,
                pady=0,
                command=lambda t=tag: self._remove_tag(t)
            )
            remove_btn.pack(side=tk.LEFT)

            self._tag_pills.append(pill_frame)

        # Show message if no tags
        if not self._current_tags:
            no_tags_label = tk.Label(self._tags_container, text="No tags", fg="gray", font=("TkDefaultFont", 8))
            no_tags_label.pack(side=tk.LEFT)

    def _add_tag_from_entry(self) -> None:
        """Add tag from entry field."""
        tag = self._tag_entry.get().strip()
        if tag and tag not in self._current_tags:
            self._current_tags.append(tag)
            self._refresh_tag_pills()
            self._tag_entry.delete(0, tk.END)
            self._autocomplete_frame.grid_remove()

    def _remove_tag(self, tag: str) -> None:
        """Remove a tag from the current tags list."""
        if tag in self._current_tags:
            self._current_tags.remove(tag)
            self._refresh_tag_pills()

    def _on_tag_entry_change(self, event) -> None:
        """Handle tag entry text change for autocomplete."""
        if not self._get_all_tags:
            return

        current_text = self._tag_entry.get().strip().lower()
        if not current_text:
            self._autocomplete_frame.grid_remove()
            return

        # Get matching tags
        all_tags = self._get_all_tags()
        matching_tags = [tag for tag in all_tags if current_text in tag.lower() and tag not in self._current_tags]

        if matching_tags:
            self._autocomplete_listbox.delete(0, tk.END)
            for tag in matching_tags[:10]:  # Show max 10 suggestions
                self._autocomplete_listbox.insert(tk.END, tag)
            self._autocomplete_frame.grid()
        else:
            self._autocomplete_frame.grid_remove()

    def _on_autocomplete_select(self, event) -> None:
        """Handle autocomplete selection."""
        selection = self._autocomplete_listbox.curselection()
        if selection:
            tag = self._autocomplete_listbox.get(selection[0])
            if tag not in self._current_tags:
                self._current_tags.append(tag)
                self._refresh_tag_pills()
            self._tag_entry.delete(0, tk.END)
            self._autocomplete_frame.grid_remove()

    def _validate_inputs(self) -> bool:
        """Validate all input fields."""
        name = self._name_var.get().strip()
        url = self._url_var.get().strip()
        
        if not name:
            messagebox.showerror("Error", "Name cannot be empty.")
            self._name_entry.focus()
            return False
        
        if not url:
            messagebox.showerror("Error", "URL cannot be empty.")
            self._url_entry.focus()
            return False
        
        # Validate date_added
        date_added = self._date_added_var.get().strip()
        if date_added and not DateFormatter.validate_datetime(date_added):
            messagebox.showerror("Error", "Invalid Date Added format. Use YYYY-MM-DDTHH:MM:SS.")
            self._date_added_entry.focus()
            return False
        
        # Validate last_opened
        last_opened = self._last_opened_var.get().strip()
        if last_opened and not DateFormatter.validate_datetime(last_opened):
            messagebox.showerror("Error", "Invalid Last Opened format. Use YYYY-MM-DDTHH:MM:SS.")
            self._last_opened_entry.focus()
            return False
        
        return True
    
    def _on_save_clicked(self) -> None:
        """Handle save button click."""
        if not self._validate_inputs():
            return

        try:
            # Create updated link preserving all existing fields
            updated_link = Link(
                name=self._name_var.get().strip(),
                url=self._url_var.get().strip(),
                favorite=self._favorite_var.get(),
                date_added=self._date_added_var.get().strip() or self._original_link.date_added,
                last_opened=self._last_opened_var.get().strip() or None,
                # Preserve all other fields from original link
                open_count=self._original_link.open_count,
                archived=self._original_link.archived,
                first_opened=self._original_link.first_opened,
                favorite_toggle_count=self._original_link.favorite_toggle_count,
                last_modified=self._original_link.last_modified,
                time_to_first_open=self._original_link.time_to_first_open,
                opens_last_30_days=self._original_link.opens_last_30_days,
                tags=self._current_tags.copy(),
                category=self._original_link.category,
                domain=self._original_link.domain,
                notes=self._original_link.notes,
                source=self._original_link.source,
                link_status=self._original_link.link_status,
                last_checked=self._original_link.last_checked,
                http_status_code=self._original_link.http_status_code
            )

            # Call save callback
            self._on_save(updated_link)
            self._dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
    
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        self._dialog.destroy() 