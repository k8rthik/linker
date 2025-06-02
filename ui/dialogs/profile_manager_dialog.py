import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Callable, Optional
from models.profile import Profile


class ProfileManagerDialog:
    """Dialog for managing profiles (create, rename, delete, set default)."""
    
    def __init__(self, parent: tk.Widget, profiles: List[Profile], current_profile: Optional[Profile]):
        self._parent = parent
        self._profiles = profiles.copy()
        self._current_profile = current_profile
        self._result = None
        
        # Callbacks
        self._on_create: Optional[Callable[[str, bool], bool]] = None
        self._on_rename: Optional[Callable[[str, str], bool]] = None
        self._on_delete: Optional[Callable[[str], bool]] = None
        self._on_set_default: Optional[Callable[[str], bool]] = None
        
        self._create_dialog()
    
    def _create_dialog(self) -> None:
        """Create the dialog window and components."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Manage Profiles")
        self._dialog.geometry("700x400")
        self._dialog.transient(self._parent)
        self._dialog.grab_set()
        
        # Center the dialog
        self._dialog.geometry("+%d+%d" % (
            self._parent.winfo_rootx() + 50,
            self._parent.winfo_rooty() + 50
        ))
        
        self._create_components()
        self._populate_profile_list()
    
    def _create_components(self) -> None:
        """Create dialog components."""
        # Main frame
        main_frame = ttk.Frame(self._dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Profile list frame
        list_frame = ttk.LabelFrame(main_frame, text="")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Profile listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self._profile_listbox = tk.Listbox(list_container, selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self._profile_listbox.yview)
        self._profile_listbox.config(yscrollcommand=scrollbar.set)
        
        self._profile_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self._profile_listbox.bind("<<ListboxSelect>>", self._on_profile_selected)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Left side buttons (profile actions)
        left_buttons = ttk.Frame(buttons_frame)
        left_buttons.pack(side=tk.LEFT)
        
        self._create_button = ttk.Button(left_buttons, text="Create New", command=self._create_profile)
        self._create_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self._rename_button = ttk.Button(left_buttons, text="Rename", command=self._rename_profile, state=tk.DISABLED)
        self._rename_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self._delete_button = ttk.Button(left_buttons, text="Delete", command=self._delete_profile, state=tk.DISABLED)
        self._delete_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self._default_button = ttk.Button(left_buttons, text="Set as Default", command=self._set_default, state=tk.DISABLED)
        self._default_button.pack(side=tk.LEFT)
        
        # Right side buttons (dialog actions)
        right_buttons = ttk.Frame(buttons_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        self._close_button = ttk.Button(right_buttons, text="Close", command=self._close_dialog)
        self._close_button.pack(side=tk.LEFT)
    
    def _populate_profile_list(self) -> None:
        """Populate the profile list."""
        self._profile_listbox.delete(0, tk.END)
        
        for profile in self._profiles:
            display_text = profile.name
            if profile.is_default:
                display_text += " (Default)"
            if self._current_profile and profile.name == self._current_profile.name:
                display_text += " (Current)"
            
            # Add link count info
            link_count = profile.get_link_count()
            display_text += f" - {link_count} links"
            
            self._profile_listbox.insert(tk.END, display_text)
    
    def _on_profile_selected(self, event) -> None:
        """Handle profile selection."""
        selection = self._profile_listbox.curselection()
        if selection:
            index = selection[0]
            profile = self._profiles[index]
            
            # Enable/disable buttons based on selection
            self._rename_button.config(state=tk.NORMAL)
            self._default_button.config(state=tk.DISABLED if profile.is_default else tk.NORMAL)
            
            # Can't delete if it's the only profile or current profile with only one profile
            can_delete = (len(self._profiles) > 1 and 
                         not (self._current_profile and profile.name == self._current_profile.name and len(self._profiles) == 1))
            self._delete_button.config(state=tk.NORMAL if can_delete else tk.DISABLED)
        else:
            self._rename_button.config(state=tk.DISABLED)
            self._delete_button.config(state=tk.DISABLED)
            self._default_button.config(state=tk.DISABLED)
    
    def _create_profile(self) -> None:
        """Create a new profile."""
        dialog = ProfileNameDialog(self._dialog, "Create New Profile")
        result = dialog.show()
        
        if result:
            name, make_default = result
            if self._on_create and self._on_create(name, make_default):
                # Refresh the profiles list if creation was successful
                self._refresh_profiles()
            else:
                messagebox.showerror("Error", f"Failed to create profile '{name}'. Name might already exist.")
    
    def _rename_profile(self) -> None:
        """Rename the selected profile."""
        selection = self._profile_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        profile = self._profiles[index]
        
        dialog = ProfileNameDialog(self._dialog, "Rename Profile", initial_name=profile.name)
        result = dialog.show()
        
        if result:
            new_name, _ = result  # Ignore make_default for rename
            if self._on_rename and self._on_rename(profile.name, new_name):
                self._refresh_profiles()
            else:
                messagebox.showerror("Error", f"Failed to rename profile. Name '{new_name}' might already exist.")
    
    def _delete_profile(self) -> None:
        """Delete the selected profile."""
        selection = self._profile_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        profile = self._profiles[index]
        
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", 
                              f"Are you sure you want to delete profile '{profile.name}'?\n"
                              f"This will permanently delete all {profile.get_link_count()} links in this profile."):
            if self._on_delete and self._on_delete(profile.name):
                self._refresh_profiles()
            else:
                messagebox.showerror("Error", f"Failed to delete profile '{profile.name}'.")
    
    def _set_default(self) -> None:
        """Set the selected profile as default."""
        selection = self._profile_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        profile = self._profiles[index]
        
        if self._on_set_default and self._on_set_default(profile.name):
            self._refresh_profiles()
        else:
            messagebox.showerror("Error", f"Failed to set '{profile.name}' as default.")
    
    def _refresh_profiles(self) -> None:
        """Refresh the profiles list (should be called from parent after changes)."""
        # This is a placeholder - the parent should call set_profiles to refresh
        pass
    
    def _close_dialog(self) -> None:
        """Close the dialog."""
        self._dialog.destroy()
    
    def show(self) -> None:
        """Show the dialog."""
        self._dialog.wait_window()
        return self._result
    
    def set_callbacks(self, on_create: Callable[[str, bool], bool],
                     on_rename: Callable[[str, str], bool],
                     on_delete: Callable[[str], bool],
                     on_set_default: Callable[[str], bool]) -> None:
        """Set the callback functions."""
        self._on_create = on_create
        self._on_rename = on_rename
        self._on_delete = on_delete
        self._on_set_default = on_set_default
    
    def update_profiles(self, profiles: List[Profile], current_profile: Optional[Profile]) -> None:
        """Update the profiles list."""
        self._profiles = profiles.copy()
        self._current_profile = current_profile
        self._populate_profile_list()


class ProfileNameDialog:
    """Dialog for entering a profile name."""
    
    def __init__(self, parent: tk.Widget, title: str, initial_name: str = ""):
        self._parent = parent
        self._title = title
        self._initial_name = initial_name
        self._result = None
        
        self._create_dialog()
    
    def _create_dialog(self) -> None:
        """Create the dialog window."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title(self._title)
        self._dialog.geometry("350x200")
        self._dialog.transient(self._parent)
        self._dialog.grab_set()
        self._dialog.resizable(False, False)
        
        # Center the dialog
        self._dialog.geometry("+%d+%d" % (
            self._parent.winfo_rootx() + 100,
            self._parent.winfo_rooty() + 100
        ))
        
        self._create_components()
    
    def _create_components(self) -> None:
        """Create dialog components."""
        main_frame = ttk.Frame(self._dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Name entry
        ttk.Label(main_frame, text="Profile Name:").pack(anchor=tk.W)
        self._name_var = tk.StringVar(value=self._initial_name)
        self._name_entry = ttk.Entry(main_frame, textvariable=self._name_var, width=40)
        self._name_entry.pack(fill=tk.X, pady=(5, 10))
        self._name_entry.focus()
        self._name_entry.select_range(0, tk.END)
        
        # Default checkbox (only for create)
        if "Create" in self._title:
            self._default_var = tk.BooleanVar()
            self._default_checkbox = ttk.Checkbutton(
                main_frame, 
                text="Set as default profile",
                variable=self._default_var
            )
            self._default_checkbox.pack(anchor=tk.W, pady=(0, 10))
        else:
            self._default_var = tk.BooleanVar()  # Dummy variable for rename
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="OK", command=self._ok_clicked).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self._cancel_clicked).pack(side=tk.RIGHT)
        
        # Bind Enter key
        self._dialog.bind("<Return>", lambda e: self._ok_clicked())
        self._dialog.bind("<Escape>", lambda e: self._cancel_clicked())
    
    def _ok_clicked(self) -> None:
        """Handle OK button click."""
        name = self._name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Profile name cannot be empty!")
            return
        
        if len(name) > 50:
            messagebox.showerror("Error", "Profile name cannot exceed 50 characters!")
            return
        
        self._result = (name, self._default_var.get())
        self._dialog.destroy()
    
    def _cancel_clicked(self) -> None:
        """Handle Cancel button click."""
        self._result = None
        self._dialog.destroy()
    
    def show(self) -> Optional[tuple]:
        """Show the dialog and return the result."""
        self._dialog.wait_window()
        return self._result 