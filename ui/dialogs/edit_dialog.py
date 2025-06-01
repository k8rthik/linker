import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional, Callable, List, Set
from models.link import Link
from utils.date_formatter import DateFormatter


class EditLinkDialog:
    """Dialog for editing link properties."""
    
    def __init__(self, parent: tk.Tk, link: Link, on_save: Callable[[Link], None], 
                 all_tags: List[str] = None):
        self._parent = parent
        self._original_link = link
        self._on_save = on_save
        self._all_tags = all_tags or []
        self._dialog: Optional[tk.Toplevel] = None
        self._current_tags: Set[str] = link.tags.copy()
        self._create_dialog()
    
    def _create_dialog(self) -> None:
        """Create and show the edit dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Edit Link")
        self._dialog.geometry("600x700")
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
        self._create_tags_section(parent)
        
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
    
    def _create_tags_section(self, parent: tk.Frame) -> None:
        """Create the tags editing section."""
        # Tags label
        tk.Label(parent, text="Tags:", font=("TkDefaultFont", 9, "bold")).grid(
            row=5, column=0, sticky="w", pady=(0, 5))
        
        # Tag input frame
        tag_input_frame = tk.Frame(parent)
        tag_input_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Tag entry with autocomplete
        self._tag_var = tk.StringVar()
        self._tag_entry = ttk.Combobox(
            tag_input_frame,
            textvariable=self._tag_var,
            width=40,
            values=self._all_tags
        )
        self._tag_entry.pack(side=tk.LEFT, padx=(0, 5))
        self._tag_entry.bind('<Return>', self._on_add_tag)
        
        # Add tag button
        add_tag_btn = tk.Button(
            tag_input_frame,
            text="Add Tag",
            command=self._on_add_tag,
            width=10
        )
        add_tag_btn.pack(side=tk.LEFT)
        
        # Tags display frame
        tags_display_frame = tk.LabelFrame(parent, text="Current Tags", font=("TkDefaultFont", 8))
        tags_display_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        # Tags listbox with scrollbar
        tags_list_frame = tk.Frame(tags_display_frame)
        tags_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self._tags_listbox = tk.Listbox(
            tags_list_frame,
            height=4,
            font=("TkDefaultFont", 8)
        )
        tags_scrollbar = ttk.Scrollbar(tags_list_frame, orient=tk.VERTICAL, command=self._tags_listbox.yview)
        self._tags_listbox.configure(yscrollcommand=tags_scrollbar.set)
        
        self._tags_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tags_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Remove tag button
        remove_tag_btn = tk.Button(
            tags_display_frame,
            text="Remove Selected",
            command=self._on_remove_selected_tags,
            font=("TkDefaultFont", 8)
        )
        remove_tag_btn.pack(pady=(0, 5))
        
        # Clear all tags button
        clear_tags_btn = tk.Button(
            tags_display_frame,
            text="Clear All",
            command=self._on_clear_all_tags,
            font=("TkDefaultFont", 8)
        )
        clear_tags_btn.pack()
        
        # Update tags display
        self._update_tags_display()
    
    def _update_tags_display(self) -> None:
        """Update the tags listbox display."""
        self._tags_listbox.delete(0, tk.END)
        for tag in sorted(self._current_tags):
            self._tags_listbox.insert(tk.END, tag)
    
    def _on_add_tag(self, event=None) -> None:
        """Handle adding a new tag."""
        tag = self._tag_var.get().strip()
        if not tag:
            return
        
        if tag in self._current_tags:
            messagebox.showinfo("Info", f"Tag '{tag}' already exists.")
            return
        
        self._current_tags.add(tag)
        self._update_tags_display()
        self._tag_var.set("")
        self._tag_entry.focus()
    
    def _on_remove_selected_tags(self) -> None:
        """Handle removing selected tags."""
        selected_indices = self._tags_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Info", "Please select tags to remove.")
            return
        
        tags_to_remove = []
        for index in selected_indices:
            tag = self._tags_listbox.get(index)
            tags_to_remove.append(tag)
        
        for tag in tags_to_remove:
            self._current_tags.discard(tag)
        
        self._update_tags_display()
    
    def _on_clear_all_tags(self) -> None:
        """Handle clearing all tags."""
        if not self._current_tags:
            return
        
        if messagebox.askyesno("Confirm", "Remove all tags?"):
            self._current_tags.clear()
            self._update_tags_display()
    
    def _create_buttons(self, parent: tk.Frame) -> None:
        """Create dialog buttons."""
        btn_frame = tk.Frame(parent)
        btn_frame.grid(row=16, column=0, columnspan=2, pady=(10, 0))
        
        save_btn = tk.Button(btn_frame, text="Save", command=self._on_save_clicked, width=10)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = tk.Button(btn_frame, text="Cancel", command=self._on_cancel_clicked, width=10)
        cancel_btn.pack(side=tk.LEFT)
    
    def _configure_dialog(self) -> None:
        """Configure dialog properties."""
        self._dialog.transient(self._parent)
        self._dialog.grab_set()
        self._name_entry.focus()
        self._name_entry.select_range(0, tk.END)
        
        # Center the dialog
        self._dialog.update_idletasks()
        x = (self._dialog.winfo_screenwidth() // 2) - (self._dialog.winfo_width() // 2)
        y = (self._dialog.winfo_screenheight() // 2) - (self._dialog.winfo_height() // 2)
        self._dialog.geometry(f"+{x}+{y}")
    
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
            # Create updated link
            updated_link = Link(
                name=self._name_var.get().strip(),
                url=self._url_var.get().strip(),
                favorite=self._favorite_var.get(),
                date_added=self._date_added_var.get().strip() or self._original_link.date_added,
                last_opened=self._last_opened_var.get().strip() or None,
                tags=self._current_tags
            )
            
            # Call save callback
            self._on_save(updated_link)
            self._dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
    
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        self._dialog.destroy() 