import tkinter as tk
from tkinter import ttk
from typing import List, Callable, Optional
from models.profile import Profile


class ProfileSelector:
    """Component for displaying and selecting profiles."""
    
    def __init__(self, parent: tk.Widget):
        self._parent = parent
        self._profiles: List[Profile] = []
        self._current_profile: Optional[Profile] = None
        
        # Callbacks
        self._on_profile_changed: Optional[Callable[[str], None]] = None
        self._on_manage_profiles: Optional[Callable[[], None]] = None
        
        self._create_components()
    
    def _create_components(self) -> None:
        """Create the profile selector components."""
        # Main frame
        self._frame = ttk.Frame(self._parent)
        
        # Profile label
        self._profile_label = ttk.Label(self._frame, text="Profile:")
        self._profile_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Profile dropdown
        self._profile_var = tk.StringVar()
        self._profile_combobox = ttk.Combobox(
            self._frame, 
            textvariable=self._profile_var,
            state="readonly",
            width=15
        )
        self._profile_combobox.bind("<<ComboboxSelected>>", self._on_profile_selected)
        self._profile_combobox.pack(side=tk.LEFT, padx=(0, 10))
        
        # Profile info label
        self._info_label = ttk.Label(self._frame, text="", foreground="gray")
        self._info_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Manage profiles button
        self._manage_button = ttk.Button(
            self._frame,
            text="Manage Profiles",
            command=self._on_manage_clicked
        )
        self._manage_button.pack(side=tk.LEFT)
    
    def pack(self, **kwargs) -> None:
        """Pack the main frame."""
        self._frame.pack(**kwargs)
    
    def grid(self, **kwargs) -> None:
        """Grid the main frame."""
        self._frame.grid(**kwargs)
    
    def set_profiles(self, profiles: List[Profile], current_profile: Optional[Profile]) -> None:
        """Set the available profiles and current selection."""
        self._profiles = profiles
        self._current_profile = current_profile
        
        # Update combobox values
        profile_names = [profile.name for profile in profiles]
        self._profile_combobox['values'] = profile_names
        
        # Set current selection
        if current_profile:
            self._profile_var.set(current_profile.name)
            self._update_info_label(current_profile)
        else:
            self._profile_var.set("")
            self._info_label.config(text="")
    
    def get_selected_profile(self) -> Optional[str]:
        """Get the currently selected profile name."""
        return self._profile_var.get() if self._profile_var.get() else None
    
    def _update_info_label(self, profile: Profile) -> None:
        """Update the info label with profile statistics."""
        link_count = profile.get_link_count()
        favorite_count = profile.get_favorite_count()
        
        info_text = f"{link_count} links"
        if favorite_count > 0:
            info_text += f" ({favorite_count} favorites)"
        
        self._info_label.config(text=info_text)
    
    def _on_profile_selected(self, event) -> None:
        """Handle profile selection."""
        selected_name = self._profile_var.get()
        if selected_name and self._on_profile_changed:
            # Find the selected profile and update info
            for profile in self._profiles:
                if profile.name == selected_name:
                    self._update_info_label(profile)
                    break
            
            self._on_profile_changed(selected_name)
    
    def _on_manage_clicked(self) -> None:
        """Handle manage profiles button click."""
        if self._on_manage_profiles:
            self._on_manage_profiles()
    
    def set_profile_changed_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for profile selection changes."""
        self._on_profile_changed = callback
    
    def set_manage_profiles_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for manage profiles button."""
        self._on_manage_profiles = callback
    
    def refresh_current_profile_info(self) -> None:
        """Refresh the info display for the current profile."""
        if self._current_profile:
            self._update_info_label(self._current_profile)