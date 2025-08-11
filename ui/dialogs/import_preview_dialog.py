import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Any, Tuple


class ImportPreviewDialog:
    """Dialog for previewing import data and selecting import options."""
    
    def __init__(self, parent: Optional[tk.Widget], import_data: Dict[str, Any], initial_mode: str = "merge"):
        self._parent = parent
        self._import_data = import_data
        self._initial_mode = initial_mode
        self._result: Optional[Tuple[str, List[str]]] = None
        
        self._dialog: Optional[tk.Toplevel] = None
        self._mode_var: Optional[tk.StringVar] = None
        self._profile_vars: Dict[str, tk.BooleanVar] = {}
        self._profile_checkboxes: List[tk.Checkbutton] = []
        
    def show(self) -> Optional[Tuple[str, List[str]]]:
        """
        Show the dialog and return user choices.
        Returns (import_mode, selected_profiles) or None if cancelled.
        """
        self._create_dialog()
        self._create_widgets()
        self._populate_data()
        
        # Center the dialog
        self._center_dialog()
        
        # Make dialog modal
        self._dialog.transient(self._parent)
        self._dialog.grab_set()
        
        # Wait for dialog to close
        self._dialog.wait_window()
        
        return self._result
    
    def _create_dialog(self) -> None:
        """Create the main dialog window."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Import Links - Preview")
        self._dialog.geometry("600x500")
        self._dialog.minsize(500, 400)
        self._dialog.resizable(True, True)
        
        # Handle window close
        self._dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _create_widgets(self) -> None:
        """Create all dialog widgets."""
        main_frame = ttk.Frame(self._dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Import Links", font=("Arial", 14, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Import summary
        self._create_summary_section(main_frame)
        
        # Import mode selection
        self._create_mode_section(main_frame)
        
        # Profile selection
        self._create_profile_section(main_frame)
        
        # Buttons
        self._create_buttons(main_frame)
    
    def _create_summary_section(self, parent: tk.Widget) -> None:
        """Create the import summary section."""
        summary_frame = ttk.LabelFrame(parent, text="Import Summary", padding="10")
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        metadata = self._import_data.get("export_metadata", {})
        
        # Export info
        info_text = f"Export Date: {metadata.get('export_date', 'Unknown')}\n"
        info_text += f"Total Profiles: {metadata.get('total_profiles', 0)}\n"
        info_text += f"Total Links: {metadata.get('total_links', 0)}\n"
        info_text += f"Export Version: {metadata.get('version', 'Unknown')}"
        
        info_label = ttk.Label(summary_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(anchor=tk.W)
    
    def _create_mode_section(self, parent: tk.Widget) -> None:
        """Create the import mode selection section."""
        mode_frame = ttk.LabelFrame(parent, text="Import Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        self._mode_var = tk.StringVar(value=self._initial_mode)
        
        merge_radio = ttk.Radiobutton(
            mode_frame, 
            text="Merge with existing data",
            variable=self._mode_var,
            value="merge"
        )
        merge_radio.pack(anchor=tk.W)
        
        merge_desc = ttk.Label(
            mode_frame,
            text="• Add imported links to existing profiles\n• Create new profiles if they don't exist",
            font=("Arial", 9),
            foreground="gray"
        )
        merge_desc.pack(anchor=tk.W, padx=(20, 0), pady=(0, 5))
        
        replace_radio = ttk.Radiobutton(
            mode_frame,
            text="Replace all existing data",
            variable=self._mode_var,
            value="replace"
        )
        replace_radio.pack(anchor=tk.W)
        
        replace_desc = ttk.Label(
            mode_frame,
            text="• Delete all existing profiles and links\n• Replace with imported data",
            font=("Arial", 9),
            foreground="gray"
        )
        replace_desc.pack(anchor=tk.W, padx=(20, 0))
    
    def _create_profile_section(self, parent: tk.Widget) -> None:
        """Create the profile selection section."""
        profile_frame = ttk.LabelFrame(parent, text="Select Profiles to Import", padding="10")
        profile_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Select all/none buttons
        button_frame = ttk.Frame(profile_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        select_all_btn = ttk.Button(
            button_frame,
            text="Select All",
            command=self._select_all_profiles
        )
        select_all_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        select_none_btn = ttk.Button(
            button_frame,
            text="Select None",
            command=self._select_no_profiles
        )
        select_none_btn.pack(side=tk.LEFT)
        
        # Scrollable profile list
        canvas_frame = ttk.Frame(profile_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Store references for later use
        self._scrollable_frame = scrollable_frame
        self._canvas = canvas
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
    
    def _create_buttons(self, parent: tk.Widget) -> None:
        """Create dialog buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        import_btn = ttk.Button(
            button_frame,
            text="Import",
            command=self._on_import
        )
        import_btn.pack(side=tk.RIGHT)
    
    def _populate_data(self) -> None:
        """Populate the dialog with import data."""
        profiles = self._import_data.get("profiles", [])
        
        # Clear existing profile checkboxes
        for checkbox in self._profile_checkboxes:
            checkbox.destroy()
        self._profile_checkboxes.clear()
        self._profile_vars.clear()
        
        # Create checkboxes for each profile
        for profile_data in profiles:
            profile_name = profile_data.get("profile_name", "Unknown")
            link_count = profile_data.get("link_count", len(profile_data.get("links", [])))
            is_default = profile_data.get("is_default", False)
            
            # Create checkbox variable (default to checked)
            var = tk.BooleanVar(value=True)
            self._profile_vars[profile_name] = var
            
            # Create checkbox frame
            checkbox_frame = ttk.Frame(self._scrollable_frame)
            checkbox_frame.pack(fill=tk.X, pady=(0, 5))
            
            # Create checkbox
            checkbox = ttk.Checkbutton(
                checkbox_frame,
                variable=var
            )
            checkbox.pack(side=tk.LEFT)
            self._profile_checkboxes.append(checkbox)
            
            # Create profile info label
            info_text = f"{profile_name}"
            if is_default:
                info_text += " (Default)"
            info_text += f" - {link_count} links"
            
            info_label = ttk.Label(
                checkbox_frame,
                text=info_text,
                font=("Arial", 10)
            )
            info_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # Create profile details (first few links as preview)
            if profile_data.get("links"):
                preview_links = profile_data["links"][:3]  # Show first 3 links
                preview_text = "Links: " + ", ".join([link.get("name", "Unknown") for link in preview_links])
                if len(profile_data["links"]) > 3:
                    preview_text += f" (and {len(profile_data['links']) - 3} more...)"
                
                preview_label = ttk.Label(
                    checkbox_frame,
                    text=preview_text,
                    font=("Arial", 8),
                    foreground="gray"
                )
                preview_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Update canvas scroll region
        self._canvas.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
    
    def _select_all_profiles(self) -> None:
        """Select all profiles for import."""
        for var in self._profile_vars.values():
            var.set(True)
    
    def _select_no_profiles(self) -> None:
        """Deselect all profiles for import."""
        for var in self._profile_vars.values():
            var.set(False)
    
    def _on_import(self) -> None:
        """Handle import button click."""
        # Get selected import mode
        import_mode = self._mode_var.get() if self._mode_var else "merge"
        
        # Get selected profiles
        selected_profiles = [
            profile_name for profile_name, var in self._profile_vars.items()
            if var.get()
        ]
        
        # Validate selection
        if not selected_profiles:
            messagebox.showwarning(
                "No Selection",
                "Please select at least one profile to import."
            )
            return
        
        # Confirm replace mode
        if import_mode == "replace":
            if not messagebox.askyesno(
                "Confirm Replace",
                "This will delete ALL existing profiles and links and replace them with the imported data.\n\n"
                "This action cannot be undone. Are you sure you want to continue?"
            ):
                return
        
        # Set result and close dialog
        self._result = (import_mode, selected_profiles)
        self._dialog.destroy()
    
    def _on_cancel(self) -> None:
        """Handle cancel button click or window close."""
        self._result = None
        self._dialog.destroy()
    
    def _center_dialog(self) -> None:
        """Center the dialog on screen or parent."""
        self._dialog.update_idletasks()
        
        if self._parent:
            # Center on parent
            parent_x = self._parent.winfo_rootx()
            parent_y = self._parent.winfo_rooty()
            parent_width = self._parent.winfo_width()
            parent_height = self._parent.winfo_height()
            
            dialog_width = self._dialog.winfo_reqwidth()
            dialog_height = self._dialog.winfo_reqheight()
            
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
        else:
            # Center on screen
            screen_width = self._dialog.winfo_screenwidth()
            screen_height = self._dialog.winfo_screenheight()
            dialog_width = self._dialog.winfo_reqwidth()
            dialog_height = self._dialog.winfo_reqheight()
            
            x = (screen_width - dialog_width) // 2
            y = (screen_height - dialog_height) // 2
        
        self._dialog.geometry(f"+{x}+{y}") 