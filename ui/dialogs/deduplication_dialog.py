import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional
from models.link import Link


class DeduplicationPreviewDialog:
    """Dialog for previewing and confirming deduplication."""

    def __init__(self, parent: tk.Tk, duplicate_groups: Dict[str, List[Link]]):
        self._parent = parent
        self._duplicate_groups = duplicate_groups
        self._dialog: Optional[tk.Toplevel] = None
        self._confirmed = False

        # Calculate statistics
        self._total_duplicates = sum(len(links) for links in duplicate_groups.values())
        self._total_groups = len(duplicate_groups)
        self._total_removable = self._total_duplicates - self._total_groups

        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create and show the preview dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Duplicate Links Found")
        self._dialog.geometry("800x500")
        self._dialog.resizable(True, True)

        # Main frame
        main_frame = ttk.Frame(self._dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Summary at top
        self._create_summary(main_frame)

        # List of duplicate groups
        self._create_duplicate_list(main_frame)

        # Buttons at bottom
        self._create_buttons(main_frame)

        # Configure dialog
        self._configure_dialog()

    def _create_summary(self, parent: ttk.Frame) -> None:
        """Create summary section."""
        summary_frame = ttk.LabelFrame(parent, text="Summary")
        summary_frame.pack(fill=tk.X, pady=(0, 10))

        summary_text = (
            f"Found {self._total_duplicates} duplicate links in {self._total_groups} groups\n"
            f"{self._total_removable} links can be removed"
        )

        ttk.Label(summary_frame, text=summary_text).pack(padx=10, pady=10)

    def _create_duplicate_list(self, parent: ttk.Frame) -> None:
        """Create list of duplicate groups."""
        list_frame = ttk.LabelFrame(parent, text="Duplicate Groups")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Create treeview with scrollbar
        tree_container = ttk.Frame(list_frame)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._tree = ttk.Treeview(tree_container, columns=("Count", "URL"), show="tree headings")
        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.config(yscrollcommand=scrollbar.set)

        # Configure columns
        self._tree.heading("#0", text="Name")
        self._tree.heading("Count", text="Duplicates")
        self._tree.heading("URL", text="URL")

        self._tree.column("#0", width=300)
        self._tree.column("Count", width=100)
        self._tree.column("URL", width=350)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate tree
        self._populate_tree()

    def _populate_tree(self) -> None:
        """Populate the tree with duplicate groups."""
        for url, links in self._duplicate_groups.items():
            # Parent item for the group
            group_name = links[0].name if links else url
            parent = self._tree.insert("", "end", text=group_name,
                                      values=(len(links), url))

            # Child items for each link
            for link in links:
                fav_marker = " [F]" if link.favorite else ""
                self._tree.insert(parent, "end", text=link.name + fav_marker,
                                values=("", link.url))

    def _create_buttons(self, parent: ttk.Frame) -> None:
        """Create dialog buttons."""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Proceed", command=self._on_proceed).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel).pack(side=tk.LEFT)

    def _configure_dialog(self) -> None:
        """Configure dialog properties."""
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

        # Bind keys
        self._dialog.bind("<Return>", lambda e: self._on_proceed())
        self._dialog.bind("<Escape>", lambda e: self._on_cancel())

        # Center dialog
        self._dialog.update_idletasks()
        x = (self._dialog.winfo_screenwidth() // 2) - (self._dialog.winfo_width() // 2)
        y = (self._dialog.winfo_screenheight() // 2) - (self._dialog.winfo_height() // 2)
        self._dialog.geometry(f"+{x}+{y}")

    def _on_proceed(self) -> None:
        """Handle proceed button."""
        self._confirmed = True
        self._dialog.destroy()

    def _on_cancel(self) -> None:
        """Handle cancel button."""
        self._confirmed = False
        self._dialog.destroy()

    def show(self) -> bool:
        """Show the dialog and return whether user confirmed."""
        if self._dialog:
            self._dialog.wait_window()
        return self._confirmed


class DeduplicationProgressDialog:
    """Dialog showing progress during deduplication."""

    def __init__(self, parent: tk.Tk, total_groups: int):
        self._parent = parent
        self._total_groups = total_groups
        self._dialog: Optional[tk.Toplevel] = None
        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create the progress dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Merging Duplicates")
        self._dialog.geometry("400x150")
        self._dialog.resizable(False, False)

        # Main frame
        main_frame = ttk.Frame(self._dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Status label
        self._status_var = tk.StringVar(value="Processing duplicate groups...")
        ttk.Label(main_frame, textvariable=self._status_var).pack(pady=(0, 10))

        # Progress bar
        self._progress_var = tk.IntVar(value=0)
        self._progress = ttk.Progressbar(main_frame, variable=self._progress_var,
                                        maximum=self._total_groups, length=350)
        self._progress.pack(pady=(0, 10))

        # Progress label
        self._progress_label = ttk.Label(main_frame, text=f"0 / {self._total_groups} groups")
        self._progress_label.pack()

        # Configure dialog
        self._dialog.transient(self._parent)

        # Center dialog
        self._dialog.update_idletasks()
        x = (self._dialog.winfo_screenwidth() // 2) - (self._dialog.winfo_width() // 2)
        y = (self._dialog.winfo_screenheight() // 2) - (self._dialog.winfo_height() // 2)
        self._dialog.geometry(f"+{x}+{y}")

    def update(self, current: int, status: str) -> None:
        """Update progress."""
        self._progress_var.set(current)
        self._status_var.set(status)
        self._progress_label.config(text=f"{current} / {self._total_groups} groups")
        self._dialog.update()

    def close(self) -> None:
        """Close the progress dialog."""
        if self._dialog:
            self._dialog.destroy()


class DeduplicationResultsDialog:
    """Dialog showing deduplication results."""

    def __init__(self, parent: tk.Tk, auto_merged: int, manually_resolved: int,
                 links_removed: int, skipped: int = 0):
        self._parent = parent
        self._auto_merged = auto_merged
        self._manually_resolved = manually_resolved
        self._links_removed = links_removed
        self._skipped = skipped
        self._dialog: Optional[tk.Toplevel] = None
        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create the results dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Deduplication Complete")
        self._dialog.geometry("400x250")
        self._dialog.resizable(False, False)

        # Main frame
        main_frame = ttk.Frame(self._dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        ttk.Label(main_frame, text="Deduplication Complete",
                 font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 15))

        # Results
        results_frame = ttk.Frame(main_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        ttk.Label(results_frame, text=f"Auto-merged groups: {self._auto_merged}").pack(anchor="w")
        ttk.Label(results_frame, text=f"Manually resolved: {self._manually_resolved}").pack(anchor="w")
        ttk.Label(results_frame, text=f"Links removed: {self._links_removed}").pack(anchor="w")

        if self._skipped > 0:
            ttk.Label(results_frame, text=f"Skipped conflicts: {self._skipped}",
                     foreground="orange").pack(anchor="w")

        # Close button
        ttk.Button(main_frame, text="OK", command=self._on_ok).pack()

        # Configure dialog
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

        # Bind keys
        self._dialog.bind("<Return>", lambda e: self._on_ok())
        self._dialog.bind("<Escape>", lambda e: self._on_ok())

        # Center dialog
        self._dialog.update_idletasks()
        x = (self._dialog.winfo_screenwidth() // 2) - (self._dialog.winfo_width() // 2)
        y = (self._dialog.winfo_screenheight() // 2) - (self._dialog.winfo_height() // 2)
        self._dialog.geometry(f"+{x}+{y}")

    def _on_ok(self) -> None:
        """Handle OK button."""
        self._dialog.destroy()

    def show(self) -> None:
        """Show the dialog."""
        if self._dialog:
            self._dialog.wait_window()
