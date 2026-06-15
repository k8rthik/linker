"""Dialog for viewing and managing archived (soft-deleted) links.

Uses the unified `LinkViewer` so columns, keyboard nav, and the right-click
action set match every other links surface in the app. The viewer runs in
`archived` mode, which swaps the Archive action for Restore + Permanent
Delete in the menu and on the Backspace key.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable, List, Optional

from models.link import Link
from ui.components.link_viewer import LinkViewer, MODE_ARCHIVED
from ui.theme import COLORS


class ArchivedLinksDialog:
    """Dialog for viewing, restoring, opening, and permanently removing archived links."""

    def __init__(
        self,
        parent: tk.Tk,
        archived_links: List[Link],
        on_restore: Optional[Callable[[List[Link]], None]] = None,
        on_permanent_delete: Optional[Callable[[List[Link]], None]] = None,
        on_open: Optional[Callable[[Link], None]] = None,
        on_edit: Optional[Callable[[Link], None]] = None,
        on_toggle_favorite: Optional[Callable[[List[Link]], None]] = None,
    ):
        self._parent = parent
        self._all_links: List[Link] = list(archived_links)
        self._visible_links: List[Link] = list(archived_links)
        self._on_restore = on_restore
        self._on_permanent_delete = on_permanent_delete
        self._on_open = on_open
        self._on_edit = on_edit
        self._on_toggle_favorite = on_toggle_favorite
        self._dialog: Optional[tk.Toplevel] = None
        self._viewer: Optional[LinkViewer] = None
        self._search_var: Optional[tk.StringVar] = None
        self._info_label: Optional[tk.Label] = None
        self._create_dialog()

    def _create_dialog(self) -> None:
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Archived Links")
        self._dialog.geometry("1000x600")

        main_frame = tk.Frame(self._dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Archived Links", font=("", 16, "bold")).pack(pady=(0, 5))
        tk.Label(
            main_frame,
            text="These links were soft-deleted. Restore to bring them back, or permanently delete to remove.",
            font=("", 9),
            fg=COLORS["muted"],
        ).pack(pady=(0, 10))

        # Search bar
        search_frame = tk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_search())
        tk.Entry(search_frame, textvariable=self._search_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

        self._info_label = tk.Label(main_frame, text="", font=("", 10))
        self._info_label.pack(pady=(0, 10), anchor="w")

        viewer_container = tk.Frame(main_frame)
        viewer_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # MODE_ARCHIVED makes the viewer swap "Archive" → "Restore" /
        # "Delete Permanently" in the right-click menu and on Backspace.
        self._viewer = LinkViewer(viewer_container, mode=MODE_ARCHIVED)
        self._viewer.pack(fill=tk.BOTH, expand=True)

        # Open is wired so it opens the link in the browser *without*
        # un-archiving it — restoring is a separate explicit action.
        if self._on_open:
            self._viewer.set_open_callback(
                lambda links: [self._on_open(link) for link in links]
            )
        if self._on_edit:
            self._viewer.set_edit_callback(self._on_edit)
        if self._on_toggle_favorite:
            self._viewer.set_toggle_favorite_callback(self._on_toggle_favorite)
        self._viewer.set_restore_callback(self._restore_links)
        self._viewer.set_permanent_delete_callback(self._permanently_delete_links)
        self._viewer.set_copy_urls_callback(self._copy_urls)
        self._viewer.set_copy_formatted_callback(self._copy_formatted)
        self._viewer.set_copy_markdown_callback(self._copy_markdown)

        self._populate()

        # Buttons mirror the menu actions for discoverability
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
            fg=COLORS["danger_dark"],
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", command=self._dialog.destroy, width=10).pack(
            side=tk.RIGHT, padx=5
        )

        self._dialog.transient(self._parent)
        self._dialog.grab_set()
        self._dialog.bind("<Escape>", lambda e: self._dialog.destroy())

    def _populate(self) -> None:
        self._viewer.set_links(self._visible_links)
        self._update_info()

    def _update_info(self) -> None:
        total = len(self._all_links)
        visible = len(self._visible_links)
        text = (
            f"Showing {total} archived link(s)"
            if visible == total
            else f"Showing {visible} of {total} archived link(s)"
        )
        self._info_label.config(text=text)

    def _apply_search(self) -> None:
        query = (self._search_var.get() or "").strip().lower()
        if not query:
            self._visible_links = list(self._all_links)
        else:
            self._visible_links = [
                link
                for link in self._all_links
                if query in link.name.lower() or query in link.url.lower()
            ]
        self._populate()

    # --- Button → viewer-action shims -------------------------------------

    def _open_selected(self) -> None:
        links = self._viewer.get_selected_links()
        if not links:
            messagebox.showinfo("No Selection", "Please select a link to open.", parent=self._dialog)
            return
        if self._on_open:
            for link in links:
                self._on_open(link)

    def _restore_selected(self) -> None:
        links = self._viewer.get_selected_links()
        if not links:
            messagebox.showinfo("No Selection", "Please select links to restore.", parent=self._dialog)
            return
        self._restore_links(links)

    def _permanently_delete_selected(self) -> None:
        links = self._viewer.get_selected_links()
        if not links:
            messagebox.showinfo(
                "No Selection",
                "Please select links to permanently delete.",
                parent=self._dialog,
            )
            return
        self._permanently_delete_links(links)

    # --- Destructive actions, callable from menu OR buttons ---------------

    def _restore_links(self, links: List[Link]) -> None:
        count = len(links)
        if not messagebox.askyesno(
            "Confirm Restore", f"Restore {count} link(s)?", parent=self._dialog
        ):
            return

        # Delegate to the service via the controller-supplied callback. The
        # controller's restore hook is responsible for un-archiving each link
        # AND going through ProfileService so the points-pool invariant is
        # maintained (a previous direct `link.unarchive()` here bypassed it).
        if self._on_restore:
            self._on_restore(links)

        restored_ids = {id(link) for link in links}
        self._all_links = [link for link in self._all_links if id(link) not in restored_ids]
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

    def _permanently_delete_links(self, links: List[Link]) -> None:
        count = len(links)
        if not messagebox.askyesno(
            "Confirm Permanent Deletion",
            f"Permanently delete {count} link(s)?\n\nThis cannot be undone.",
            icon="warning",
            parent=self._dialog,
        ):
            return

        if self._on_permanent_delete:
            self._on_permanent_delete(links)

        deleted_ids = {id(link) for link in links}
        self._all_links = [link for link in self._all_links if id(link) not in deleted_ids]
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

    # --- Copy helpers (clipboard, scoped to the dialog) -------------------

    def _copy_payload(self, payload: str) -> None:
        try:
            self._dialog.clipboard_clear()
            self._dialog.clipboard_append(payload)
            self._dialog.update_idletasks()
        except tk.TclError:
            pass

    def _copy_urls(self, links: List[Link]) -> None:
        self._copy_payload("\n".join(link.url for link in links))

    def _copy_formatted(self, links: List[Link]) -> None:
        self._copy_payload("\n".join(f"{link.name} - {link.url}" for link in links))

    def _copy_markdown(self, links: List[Link]) -> None:
        self._copy_payload("\n".join(f"[{link.name}]({link.url})" for link in links))
