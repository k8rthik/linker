"""
Dialog for viewing and managing archived (soft-deleted) links.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Callable
from models.link import Link
from utils.date_formatter import DateFormatter


class ArchivedLinksDialog:
    """Dialog for viewing and restoring archived links."""

    def __init__(self, parent: tk.Tk, archived_links: List[Link],
                 on_restore: Optional[Callable[[List[Link]], None]] = None):
        """
        Initialize the archived links dialog.

        Args:
            parent: Parent window
            archived_links: List of archived links to display
            on_restore: Callback when links are restored (receives list of Link objects)
        """
        self._parent = parent
        self._archived_links = archived_links
        self._on_restore = on_restore
        self._dialog = None
        self._tree = None
        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create and show the archived links dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Archived Links")
        self._dialog.geometry("800x500")

        # Main frame
        main_frame = tk.Frame(self._dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(main_frame, text="Archived Links", font=("", 16, "bold"))
        title_label.pack(pady=(0, 10))

        # Info label
        info_text = f"Showing {len(self._archived_links)} archived link(s)"
        info_label = tk.Label(main_frame, text=info_text, font=("", 10))
        info_label.pack(pady=(0, 10))

        # Tree view frame
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # Tree view
        columns = ("name", "url", "date_added", "last_opened")
        self._tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                   yscrollcommand=vsb.set, xscrollcommand=hsb.set,
                                   selectmode="extended")

        # Configure scrollbars
        vsb.config(command=self._tree.yview)
        hsb.config(command=self._tree.xview)

        # Configure columns
        self._tree.heading("name", text="Name")
        self._tree.heading("url", text="URL")
        self._tree.heading("date_added", text="Date Added")
        self._tree.heading("last_opened", text="Last Opened")

        self._tree.column("name", width=200)
        self._tree.column("url", width=300)
        self._tree.column("date_added", width=120)
        self._tree.column("last_opened", width=120)

        self._tree.pack(fill=tk.BOTH, expand=True)

        # Populate tree
        self._populate_tree()

        # Button frame
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(pady=(10, 0))

        # Restore button
        restore_btn = tk.Button(btn_frame, text="Restore Selected",
                                command=self._restore_selected, width=15)
        restore_btn.pack(side=tk.LEFT, padx=5)

        # Close button
        close_btn = tk.Button(btn_frame, text="Close",
                              command=self._dialog.destroy, width=15)
        close_btn.pack(side=tk.LEFT, padx=5)

        # Configure dialog
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

        # Bind double-click to restore
        self._tree.bind("<Double-1>", lambda e: self._restore_selected())

    def _populate_tree(self) -> None:
        """Populate the tree with archived links."""
        for link in self._archived_links:
            date_added = DateFormatter.format_datetime(link.date_added)
            last_opened = DateFormatter.format_datetime(link.last_opened) if link.last_opened else "Never"

            self._tree.insert("", tk.END, values=(
                link.name,
                link.url,
                date_added,
                last_opened
            ))

    def _restore_selected(self) -> None:
        """Restore the selected archived links."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select links to restore.")
            return

        # Get selected links
        selected_indices = [self._tree.index(item) for item in selection]
        selected_links = [self._archived_links[i] for i in selected_indices]

        # Confirm restoration
        count = len(selected_links)
        msg = f"Restore {count} link(s)?"
        if not messagebox.askyesno("Confirm Restore", msg):
            return

        # Unarchive the links
        for link in selected_links:
            link.unarchive()

        # Call the restore callback if provided
        if self._on_restore:
            self._on_restore(selected_links)

        # Remove restored items from tree
        for item in selection:
            self._tree.delete(item)

        # Update info label
        remaining = len(self._tree.get_children())
        if remaining == 0:
            messagebox.showinfo("Success", f"Restored {count} link(s). No archived links remaining.")
            self._dialog.destroy()
        else:
            messagebox.showinfo("Success", f"Restored {count} link(s).")
