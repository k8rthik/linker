import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple
from models.link import Link
from utils.date_formatter import DateFormatter


class MergeConflictDialog:
    """Dialog for manually resolving link merge conflicts."""

    def __init__(self, parent: tk.Tk, link1: Link, link2: Link):
        self._parent = parent
        self._link1 = link1
        self._link2 = link2
        self._dialog: Optional[tk.Toplevel] = None
        self._result: Optional[Tuple[str, Optional[str]]] = None
        self._choice_var = tk.StringVar(value="link1")
        self._custom_name_var = tk.StringVar()
        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create and show the conflict resolution dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Merge Conflict")
        self._dialog.geometry("700x600")
        self._dialog.resizable(True, True)

        # Main frame
        main_frame = ttk.Frame(self._dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Explanation
        ttk.Label(main_frame,
                 text="These duplicate links have different custom names.\nChoose which name to keep:",
                 font=("TkDefaultFont", 10)).pack(pady=(0, 15))

        # URL display
        url_frame = ttk.LabelFrame(main_frame, text="Common URL")
        url_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(url_frame, text=self._link1.url, wraplength=650).pack(padx=10, pady=10)

        # Comparison frame
        comparison_frame = ttk.Frame(main_frame)
        comparison_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Link 1 column
        self._create_link_column(comparison_frame, self._link1, "link1", 0)

        # Link 2 column
        self._create_link_column(comparison_frame, self._link2, "link2", 1)

        # Configure grid weights
        comparison_frame.columnconfigure(0, weight=1)
        comparison_frame.columnconfigure(1, weight=1)

        # Custom name option
        custom_frame = ttk.LabelFrame(main_frame, text="Or Enter Custom Name")
        custom_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Radiobutton(custom_frame, text="Use custom name:",
                       variable=self._choice_var, value="custom").pack(anchor="w", padx=10, pady=(10, 5))

        self._custom_name_entry = ttk.Entry(custom_frame, textvariable=self._custom_name_var, width=60)
        self._custom_name_entry.pack(padx=10, pady=(0, 10), fill=tk.X)
        self._custom_name_entry.bind("<FocusIn>", lambda e: self._choice_var.set("custom"))

        # Buttons
        self._create_buttons(main_frame)

        # Configure dialog
        self._configure_dialog()

    def _create_link_column(self, parent: ttk.Frame, link: Link, value: str, column: int) -> None:
        """Create a column showing link details."""
        frame = ttk.LabelFrame(parent, text=f"Link {column + 1}")
        frame.grid(row=0, column=column, sticky="nsew", padx=5)

        # Radio button
        ttk.Radiobutton(frame, text="Use this name",
                       variable=self._choice_var, value=value).pack(anchor="w", padx=10, pady=(10, 15))

        # Details
        details_frame = ttk.Frame(frame)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self._add_field(details_frame, "Name:", link.name, 0)
        ttk.Separator(details_frame, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=2,
                                                                sticky="ew", pady=10)
        self._add_field(details_frame, "Favorite:", "Yes" if link.favorite else "No", 2)
        self._add_field(details_frame, "Date Added:", DateFormatter.format_datetime(link.date_added), 3)
        self._add_field(details_frame, "Last Opened:", DateFormatter.format_datetime(link.last_opened), 4)
        self._add_field(details_frame, "Open Count:", str(link.open_count), 5)
        self._add_field(details_frame, "Tags:", ", ".join(link.tags) if link.tags else "None", 6)

        details_frame.columnconfigure(1, weight=1)

    def _add_field(self, parent: ttk.Frame, label: str, value: str, row: int) -> None:
        """Add a field display to the frame."""
        ttk.Label(parent, text=label, font=("TkDefaultFont", 9, "bold")).grid(
            row=row, column=0, sticky="w", pady=3)
        ttk.Label(parent, text=value).grid(row=row, column=1, sticky="w", padx=(10, 0), pady=3)

    def _create_buttons(self, parent: ttk.Frame) -> None:
        """Create dialog buttons."""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=(10, 0))

        ttk.Button(btn_frame, text="Merge Links", command=self._on_merge_clicked, width=15).pack(
            side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Skip (Keep Both)", command=self._on_skip_clicked, width=15).pack(
            side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel All", command=self._on_cancel_clicked, width=15).pack(
            side=tk.LEFT, padx=5)

    def _configure_dialog(self) -> None:
        """Configure dialog properties."""
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

        # Bind keyboard shortcuts
        self._dialog.bind("<Escape>", lambda e: self._on_cancel_clicked())
        self._dialog.bind("<Return>", lambda e: self._on_merge_clicked())

        # Center dialog
        self._dialog.update_idletasks()
        x = (self._dialog.winfo_screenwidth() // 2) - (self._dialog.winfo_width() // 2)
        y = (self._dialog.winfo_screenheight() // 2) - (self._dialog.winfo_height() // 2)
        self._dialog.geometry(f"+{x}+{y}")

    def _validate_choice(self) -> bool:
        """Validate the user's choice."""
        if self._choice_var.get() == "custom":
            custom_name = self._custom_name_var.get().strip()
            if not custom_name:
                messagebox.showerror("Error", "Please enter a custom name or select one of the existing names.")
                self._custom_name_entry.focus()
                return False
        return True

    def _on_merge_clicked(self) -> None:
        """Handle merge button click."""
        if not self._validate_choice():
            return

        choice = self._choice_var.get()
        custom_name = self._custom_name_var.get().strip() if choice == "custom" else None
        self._result = (choice, custom_name)
        self._dialog.destroy()

    def _on_skip_clicked(self) -> None:
        """Handle skip button click."""
        self._result = ("skip", None)
        self._dialog.destroy()

    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        self._result = ("cancel", None)
        self._dialog.destroy()

    def show(self) -> Optional[Tuple[str, Optional[str]]]:
        """Show the dialog and wait for user input."""
        self._parent.wait_window(self._dialog)
        return self._result
