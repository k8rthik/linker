import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable
from models.link import Link
from utils.date_formatter import DateFormatter


class EditLinkDialog:
    """Dialog for editing link properties."""
    
    def __init__(self, parent: tk.Tk, link: Link, on_save: Callable[[Link], None]):
        self._parent = parent
        self._original_link = link
        self._on_save = on_save
        self._dialog: Optional[tk.Toplevel] = None
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
        
        # Date Added field
        tk.Label(parent, text="Date Added:", font=("TkDefaultFont", 9, "bold")).grid(
            row=5, column=0, sticky="w", pady=(0, 5))
        self._date_added_var = tk.StringVar(value=self._original_link.date_added)
        self._date_added_entry = tk.Entry(parent, textvariable=self._date_added_var, width=30)
        self._date_added_entry.grid(row=6, column=0, sticky="ew", pady=(0, 5))
        
        # Date format help text
        tk.Label(parent, text="Format: YYYY-MM-DDTHH:MM:SS (ISO format)", 
                font=("TkDefaultFont", 8), fg="gray").grid(row=7, column=0, sticky="w", pady=(0, 15))
        
        # Last Opened field
        tk.Label(parent, text="Last Opened:", font=("TkDefaultFont", 9, "bold")).grid(
            row=8, column=0, sticky="w", pady=(0, 5))
        self._last_opened_var = tk.StringVar(value=self._original_link.last_opened or "")
        self._last_opened_entry = tk.Entry(parent, textvariable=self._last_opened_var, width=30)
        self._last_opened_entry.grid(row=9, column=0, sticky="ew", pady=(0, 5))
        
        # Last opened help text
        tk.Label(parent, text="Format: YYYY-MM-DDTHH:MM:SS (leave empty for 'never opened')", 
                font=("TkDefaultFont", 8), fg="gray").grid(row=10, column=0, sticky="w", pady=(0, 20))
        
        # Configure grid weights
        parent.columnconfigure(0, weight=1)
    
    def _create_buttons(self, parent: tk.Frame) -> None:
        """Create dialog buttons."""
        btn_frame = tk.Frame(parent)
        btn_frame.grid(row=11, column=0, columnspan=2, pady=(10, 0))
        
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
                last_opened=self._last_opened_var.get().strip() or None
            )
            
            # Call save callback
            self._on_save(updated_link)
            self._dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
    
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        self._dialog.destroy() 