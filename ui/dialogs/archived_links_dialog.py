"""
Dialog for viewing and managing archived (soft-deleted) links.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Callable
from models.link import Link
from utils.date_formatter import DateFormatter


class ArchivedLinksDialog:
    """Dialog for viewing, restoring, opening, and permanently removing archived links."""

    def __init__(
        self,
        parent: tk.Tk,
        archived_links: List[Link],
        on_restore: Optional[Callable[[List[Link]], None]] = None,
        on_permanent_delete: Optional[Callable[[List[Link]], None]] = None,
        on_open: Optional[Callable[[Link], None]] = None,
    ):
        """
        Initialize the archived links dialog.

        Args:
            parent: Parent window
            archived_links: List of archived links to display
            on_restore: Callback when links are restored (receives list of Link objects)
            on_permanent_delete: Callback when links are permanently deleted
            on_open: Callback to open a single archived link in the browser
        """
        self._parent = parent
        # Keep a stable working copy so iteration order matches the tree rows
        self._all_links: List[Link] = list(archived_links)
        self._visible_links: List[Link] = list(archived_links)
        self._on_restore = on_restore
        self._on_permanent_delete = on_permanent_delete
        self._on_open = on_open
        self._dialog: Optional[tk.Toplevel] = None
        self._tree: Optional[ttk.Treeview] = None
        self._search_var: Optional[tk.StringVar] = None
        self._info_label: Optional[tk.Label] = None
        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create and show the archived links dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Archived Links")
        self._dialog.geometry("900x550")

        main_frame = tk.Frame(self._dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(main_frame, text="Archived Links", font=("", 16, "bold"))
        title_label.pack(pady=(0, 5))

        subtitle = tk.Label(
            main_frame,
            text="These links were soft-deleted. Restore to bring them back, or permanently delete to remove.",
            font=("", 9),
            fg="#666666",
        )
        subtitle.pack(pady=(0, 10))

        # Search bar
        search_frame = tk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_search())
        search_entry = tk.Entry(search_frame, textvariable=self._search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._info_label = tk.Label(main_frame, text="", font=("", 10))
        self._info_label.pack(pady=(0, 10), anchor="w")

        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        columns = ("favorite", "name", "url", "date_added", "last_opened", "open_count")
        self._tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode="extended",
        )

        vsb.config(command=self._tree.yview)
        hsb.config(command=self._tree.xview)

        self._tree.heading("favorite", text="★")
        self._tree.heading("name", text="Name")
        self._tree.heading("url", text="URL")
        self._tree.heading("date_added", text="Date Added")
        self._tree.heading("last_opened", text="Last Opened")
        self._tree.heading("open_count", text="Opens")

        self._tree.column("favorite", width=30, anchor="center", stretch=False)
        self._tree.column("name", width=220)
        self._tree.column("url", width=300)
        self._tree.column("date_added", width=120, anchor="center")
        self._tree.column("last_opened", width=120, anchor="center")
        self._tree.column("open_count", width=60, anchor="center", stretch=False)

        self._tree.pack(fill=tk.BOTH, expand=True)

        self._populate_tree()

        # Buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        tk.Button(
            btn_frame, text="Open in Browser", command=self._open_selected, width=16
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            btn_frame, text="Restore Selected", command=self._restore_selected, width=16
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            btn_frame,
            text="Delete Permanently",
            command=self._permanently_delete_selected,
            width=18,
            fg="#a00000",
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Close", command=self._dialog.destroy, width=10).pack(
            side=tk.RIGHT, padx=5
        )

        self._dialog.transient(self._parent)
        self._dialog.grab_set()

        self._tree.bind("<Double-1>", lambda e: self._open_selected())
        self._tree.bind("<Return>", lambda e: self._open_selected())
        self._dialog.bind("<Escape>", lambda e: self._dialog.destroy())

    def _populate_tree(self) -> None:
        """Populate the tree with the currently visible links."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        for link in self._visible_links:
            date_added = DateFormatter.format_datetime(link.date_added)
            last_opened = (
                DateFormatter.format_datetime(link.last_opened)
                if link.last_opened
                else "Never"
            )
            star = "★" if link.favorite else ""
            self._tree.insert(
                "",
                tk.END,
                values=(star, link.name, link.url, date_added, last_opened, link.open_count),
            )

        self._update_info()

    def _update_info(self) -> None:
        """Update the info label with current counts."""
        total = len(self._all_links)
        visible = len(self._visible_links)
        if visible == total:
            text = f"Showing {total} archived link(s)"
        else:
            text = f"Showing {visible} of {total} archived link(s)"
        self._info_label.config(text=text)

    def _apply_search(self) -> None:
        """Filter visible links by the search query."""
        query = (self._search_var.get() or "").strip().lower()
        if not query:
            self._visible_links = list(self._all_links)
        else:
            self._visible_links = [
                link
                for link in self._all_links
                if query in link.name.lower() or query in link.url.lower()
            ]
        self._populate_tree()

    def _selected_links(self) -> List[Link]:
        """Return the Link objects corresponding to the current tree selection."""
        selection = self._tree.selection()
        if not selection:
            return []
        indices = [self._tree.index(item) for item in selection]
        return [self._visible_links[i] for i in indices if 0 <= i < len(self._visible_links)]

    def _open_selected(self) -> None:
        """Open the selected archived links in the browser."""
        selected = self._selected_links()
        if not selected:
            messagebox.showinfo("No Selection", "Please select a link to open.", parent=self._dialog)
            return
        if not self._on_open:
            return
        for link in selected:
            self._on_open(link)

    def _restore_selected(self) -> None:
        """Restore the selected archived links."""
        selected = self._selected_links()
        if not selected:
            messagebox.showinfo("No Selection", "Please select links to restore.", parent=self._dialog)
            return

        count = len(selected)
        if not messagebox.askyesno(
            "Confirm Restore", f"Restore {count} link(s)?", parent=self._dialog
        ):
            return

        for link in selected:
            link.unarchive()

        if self._on_restore:
            self._on_restore(selected)

        # Drop restored links from the working set
        restored_set = {id(link) for link in selected}
        self._all_links = [link for link in self._all_links if id(link) not in restored_set]
        self._apply_search()

        if not self._all_links:
            messagebox.showinfo(
                "Success",
                f"Restored {count} link(s). No archived links remaining.",
                parent=self._dialog,
            )
            self._dialog.destroy()
        else:
            messagebox.showinfo("Success", f"Restored {count} link(s).", parent=self._dialog)

    def _permanently_delete_selected(self) -> None:
        """Permanently remove the selected links from the profile."""
        selected = self._selected_links()
        if not selected:
            messagebox.showinfo(
                "No Selection",
                "Please select links to permanently delete.",
                parent=self._dialog,
            )
            return

        count = len(selected)
        if not messagebox.askyesno(
            "Confirm Permanent Deletion",
            f"Permanently delete {count} link(s)?\n\nThis cannot be undone.",
            icon="warning",
            parent=self._dialog,
        ):
            return

        if self._on_permanent_delete:
            self._on_permanent_delete(selected)

        deleted_set = {id(link) for link in selected}
        self._all_links = [link for link in self._all_links if id(link) not in deleted_set]
        self._apply_search()

        if not self._all_links:
            messagebox.showinfo(
                "Success",
                f"Permanently deleted {count} link(s). No archived links remaining.",
                parent=self._dialog,
            )
            self._dialog.destroy()
        else:
            messagebox.showinfo(
                "Success", f"Permanently deleted {count} link(s).", parent=self._dialog
            )
