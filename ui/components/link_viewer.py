"""Unified link viewer used by every list-of-links UI in the app.

Single component, single column catalog, single action menu. The host wires
up callbacks for the operations it wants to expose; the viewer takes care of
columns, formatting, multi-select, keyboard nav, sort indicators, and the
right-click menu.

Design rules:
- One canonical column set is shown everywhere (`CANONICAL_COLUMNS`). Hosts
  may *add* synthetic columns via `extra_columns=[...]` but cannot subtract
  from the canonical set — that's the consistency guarantee.
- The full operation menu (open, edit, toggle favorite/read, archive or
  restore/permanent-delete depending on mode, copy URL/Name+URL/Markdown,
  view stats) is available everywhere a host wires its callbacks. Menu
  items whose callbacks are not wired are simply omitted.
- The viewer is mode-aware: `mode="active"` exposes an Archive action;
  `mode="archived"` swaps it for Restore + Permanent Delete.
"""

from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional

from models.link import Link
from ui.components.link_marker import format_link_marker
from utils.date_formatter import DateFormatter


# ---------------------------------------------------------------------------
# Column catalog
# ---------------------------------------------------------------------------

CANONICAL_COLUMNS: List[str] = [
    "favorite",
    "name",
    "url",
    "points",
    "date_added",
    "last_opened",
    "open_count",
]


@dataclass(frozen=True)
class _ColumnSpec:
    key: str
    heading: str
    width: int
    minwidth: int
    anchor: str
    stretch: bool
    sortable: bool


_CANONICAL_SPECS: Dict[str, _ColumnSpec] = {
    "favorite": _ColumnSpec("favorite", "★", 50, 50, "center", False, True),
    "name": _ColumnSpec("name", "Name", 220, 120, "w", True, True),
    "url": _ColumnSpec("url", "URL", 280, 150, "w", True, True),
    "points": _ColumnSpec("points", "Points", 65, 55, "e", False, True),
    "date_added": _ColumnSpec("date_added", "Date Added", 130, 110, "center", False, True),
    "last_opened": _ColumnSpec("last_opened", "Last Opened", 130, 110, "center", False, True),
    "open_count": _ColumnSpec("open_count", "Opens", 60, 50, "center", False, True),
}

_EXTRA_SPECS: Dict[str, _ColumnSpec] = {
    "rank": _ColumnSpec("rank", "#", 40, 40, "center", False, False),
    "score": _ColumnSpec("score", "Score", 60, 50, "e", False, True),
    "reason": _ColumnSpec("reason", "Reason", 240, 160, "w", True, False),
    "health_status": _ColumnSpec("health_status", "Status", 80, 70, "center", False, True),
    "http_code": _ColumnSpec("http_code", "HTTP", 70, 60, "center", False, True),
    "category": _ColumnSpec("category", "Category", 110, 80, "w", False, True),
    "domain": _ColumnSpec("domain", "Domain", 140, 100, "w", True, True),
    "read_status": _ColumnSpec("read_status", "Status", 70, 60, "center", False, True),
}


def _canonical_value(link: Link, key: str) -> str:
    """Render a canonical column value from a Link."""
    if key == "favorite":
        return format_link_marker(link)
    if key == "name":
        return link.name
    if key == "url":
        return link.url
    if key == "points":
        return f"{link.points:.1f}"
    if key == "date_added":
        return DateFormatter.format_datetime(link.date_added)
    if key == "last_opened":
        return DateFormatter.format_datetime(link.last_opened) if link.last_opened else "Never"
    if key == "open_count":
        return str(link.open_count)
    return ""


# ---------------------------------------------------------------------------
# LinkViewer
# ---------------------------------------------------------------------------

MODE_ACTIVE = "active"
MODE_ARCHIVED = "archived"


class LinkViewer:
    """Tkinter component that renders a list of Links with a shared UX."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        extra_columns: Optional[List[str]] = None,
        mode: str = MODE_ACTIVE,
        height: int = 20,
        selectmode: str = "extended",
    ):
        if mode not in (MODE_ACTIVE, MODE_ARCHIVED):
            raise ValueError(f"Invalid mode: {mode}")

        self._parent = parent
        self._mode = mode
        self._height = height
        self._selectmode = selectmode

        # Column order: extras-before-canonical so rank/reason sit on the left
        # where the eye expects them, with the canonical block trailing.
        extras = list(extra_columns or [])
        unknown = [c for c in extras if c not in _EXTRA_SPECS]
        if unknown:
            raise ValueError(f"Unknown extra column(s): {unknown}")
        self._extra_columns = extras
        self._columns: List[str] = extras + CANONICAL_COLUMNS

        # Data
        self._links: List[Link] = []
        self._extra_data: Optional[Callable[[Link, int], Dict[str, object]]] = None

        # Sort indicator state
        self._sort_column: Optional[str] = None
        self._sort_reverse: bool = False

        # Callback registry — None means "not exposed in menu"
        self._on_open: Optional[Callable[[List[Link]], None]] = None
        self._on_open_in_browser: Optional[Callable[[List[Link]], None]] = None
        self._on_edit: Optional[Callable[[Link], None]] = None
        self._on_toggle_favorite: Optional[Callable[[List[Link]], None]] = None
        self._on_toggle_read: Optional[Callable[[List[Link]], None]] = None
        self._on_archive: Optional[Callable[[List[Link]], None]] = None
        self._on_restore: Optional[Callable[[List[Link]], None]] = None
        self._on_permanent_delete: Optional[Callable[[List[Link]], None]] = None
        self._on_copy_urls: Optional[Callable[[List[Link]], None]] = None
        self._on_copy_formatted: Optional[Callable[[List[Link]], None]] = None
        self._on_copy_markdown: Optional[Callable[[List[Link]], None]] = None
        self._on_view_stats: Optional[Callable[[Link], None]] = None
        self._on_sort: Optional[Callable[[str, bool], None]] = None
        self._on_extend_menu: Optional[Callable[[List[Link], tk.Menu], None]] = None

        self._build()

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        self._frame = tk.Frame(self._parent)

        self._tree = ttk.Treeview(
            self._frame,
            columns=self._columns,
            show="headings",
            height=self._height,
            selectmode=self._selectmode,
        )

        for col in self._columns:
            spec = _CANONICAL_SPECS.get(col) or _EXTRA_SPECS[col]
            self._tree.heading(col, text=spec.heading)
            self._tree.column(
                col,
                width=spec.width,
                minwidth=spec.minwidth,
                anchor=spec.anchor,
                stretch=spec.stretch,
            )
            if spec.sortable:
                self._tree.heading(
                    col, text=spec.heading, command=lambda c=col: self._on_header_clicked(c)
                )

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(self._frame, orient=tk.VERTICAL, command=self._tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.config(yscrollcommand=vsb.set)

        self._bind_events()

    def _bind_events(self) -> None:
        self._tree.bind("<Double-Button-1>", self._handle_double_click)
        self._tree.bind("<Return>", self._handle_return)
        self._tree.bind("<BackSpace>", self._handle_backspace)
        self._tree.bind("<KeyPress-space>", self._handle_space)

        # Right-click — Button-2 (macOS), Button-3 (Linux/Windows), Ctrl+Click
        self._tree.bind("<Button-2>", self._handle_right_click)
        self._tree.bind("<Button-3>", self._handle_right_click)
        self._tree.bind("<Control-Button-1>", self._handle_right_click)

        # Keyboard navigation
        self._tree.bind("<Up>", lambda e: self._nav("up"))
        self._tree.bind("<Down>", lambda e: self._nav("down"))
        self._tree.bind("<Home>", lambda e: self._nav("home"))
        self._tree.bind("<End>", lambda e: self._nav("end"))
        self._tree.bind("<Prior>", lambda e: self._nav("page_up"))
        self._tree.bind("<Next>", lambda e: self._nav("page_down"))
        self._tree.bind("<Left>", lambda e: "break")
        self._tree.bind("<Right>", lambda e: "break")

        # Extended selection
        self._tree.bind("<Shift-Up>", lambda e: self._nav("up", extend=True))
        self._tree.bind("<Shift-Down>", lambda e: self._nav("down", extend=True))
        self._tree.bind("<Shift-Home>", lambda e: self._nav_shift_anchor("home"))
        self._tree.bind("<Shift-End>", lambda e: self._nav_shift_anchor("end"))
        self._tree.bind("<Shift-Prior>", lambda e: self._nav("page_up", extend=True))
        self._tree.bind("<Shift-Next>", lambda e: self._nav("page_down", extend=True))

        # Select all
        select_all = "<Command-a>" if sys.platform == "darwin" else "<Control-a>"
        self._tree.bind(select_all, self._handle_select_all)

        # Copy shortcut (when wired)
        copy_seqs = ["<Command-c>", "<Control-c>"]
        for seq in copy_seqs:
            self._tree.bind(seq, lambda e: self._invoke_if_set(self._on_copy_urls))

    # ---------------------------------------------------------------- layout

    def pack(self, **kwargs) -> None:
        self._frame.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        self._frame.grid(**kwargs)

    def get_frame(self) -> tk.Frame:
        return self._frame

    # ------------------------------------------------------------------ data

    def set_links(
        self,
        links: List[Link],
        *,
        extra_data: Optional[Callable[[Link, int], Dict[str, object]]] = None,
    ) -> None:
        """Replace the displayed links.

        Args:
            links: ordered list to render.
            extra_data: optional callable that, given (link, zero_based_rank),
                returns a dict of values for any extra (non-canonical) columns.
                Required if `extra_columns` includes any keys without a
                Link-derived default; otherwise blanks are shown.
        """
        self._links = list(links)
        self._extra_data = extra_data

        self._tree.delete(*self._tree.get_children())
        for idx, link in enumerate(self._links):
            values = self._row_values(link, idx)
            self._tree.insert("", "end", iid=str(idx), values=values)

    def _row_values(self, link: Link, idx: int) -> tuple:
        extras = self._extra_data(link, idx) if self._extra_data else {}
        values = []
        for col in self._columns:
            if col in _CANONICAL_SPECS:
                values.append(_canonical_value(link, col))
            elif col == "rank":
                values.append(extras.get("rank", idx + 1))
            else:
                raw = extras.get(col, "")
                values.append("" if raw is None else str(raw))
        return tuple(values)

    # ------------------------------------------------------------- selection

    def get_selected_links(self) -> List[Link]:
        return [self._links[int(iid)] for iid in self._tree.selection()
                if iid.isdigit() and int(iid) < len(self._links)]

    def get_selected_indices(self) -> List[int]:
        return [int(iid) for iid in self._tree.selection() if iid.isdigit()]

    def get_visual_positions_of_selected(self) -> List[int]:
        all_items = self._tree.get_children()
        return [all_items.index(iid) for iid in self._tree.selection() if iid in all_items]

    def clear_selection(self) -> None:
        self._tree.selection_clear()

    def select_indices(self, indices: List[int]) -> None:
        self._tree.selection_clear()
        for i in indices:
            iid = str(i)
            if self._tree.exists(iid):
                self._tree.selection_add(iid)

    def select_and_scroll_to(self, index: int) -> None:
        iid = str(index)
        if self._tree.exists(iid):
            self._tree.selection_set(iid)
            self._tree.focus(iid)
            self._tree.see(iid)

    def select_and_scroll_to_link(self, link: Link) -> None:
        for idx, candidate in enumerate(self._links):
            if candidate is link:
                self.select_and_scroll_to(idx)
                return

    def select_by_visual_position(self, position: int) -> None:
        all_items = self._tree.get_children()
        if 0 <= position < len(all_items):
            iid = all_items[position]
            self._tree.selection_set(iid)
            self._tree.focus(iid)
            self._tree.see(iid)

    def has_focus(self) -> bool:
        try:
            return self._tree.focus_get() is self._tree
        except KeyError:
            return False

    def focus(self, auto_select_first: bool = False) -> None:
        self._tree.focus_set()
        items = self._tree.get_children()
        if not items:
            return
        current = self._tree.focus()
        selected = self._tree.selection()
        if selected:
            if current not in selected:
                self._tree.focus(selected[0])
        elif current and current in items:
            pass
        elif auto_select_first:
            self._tree.selection_set(items[0])
            self._tree.focus(items[0])

    # ---------------------------------------------------------------- sort

    def set_sort_indicator(self, column: Optional[str], reverse: bool = False) -> None:
        """Update header arrows. Does not re-sort — the host owns sort order."""
        self._sort_column = column
        self._sort_reverse = reverse
        for col in self._columns:
            spec = _CANONICAL_SPECS.get(col) or _EXTRA_SPECS[col]
            heading = spec.heading
            if column == col:
                heading = f"{spec.heading} {'↓' if reverse else '↑'}"
            cmd = (lambda c=col: self._on_header_clicked(c)) if spec.sortable else ""
            self._tree.heading(col, text=heading, command=cmd)

    def _on_header_clicked(self, column: str) -> None:
        if not self._on_sort:
            return
        reverse = False
        if self._sort_column == column:
            reverse = not self._sort_reverse
        self._on_sort(column, reverse)

    # -------------------------------------------------------- event handlers

    def _handle_double_click(self, event) -> str:
        links = self.get_selected_links()
        if links and self._on_open:
            self._on_open(links)
        return "break"

    def _handle_return(self, event) -> str:
        # Enter prefers Edit when a single link is selected (matches main view
        # expectations), falling back to Open for multi-select.
        links = self.get_selected_links()
        if len(links) == 1 and self._on_edit:
            self._on_edit(links[0])
        elif links and self._on_open:
            self._on_open(links)
        return "break"

    def _handle_backspace(self, event) -> str:
        links = self.get_selected_links()
        if not links:
            return "break"
        if self._mode == MODE_ACTIVE and self._on_archive:
            self._on_archive(links)
        elif self._mode == MODE_ARCHIVED and self._on_permanent_delete:
            self._on_permanent_delete(links)
        return "break"

    def _handle_space(self, event) -> str:
        links = self.get_selected_links()
        if links and self._on_open:
            self._on_open(links)
        return "break"

    def _handle_select_all(self, event) -> str:
        items = self._tree.get_children()
        if items:
            self._tree.selection_set(items)
            self._tree.focus(items[0])
        return "break"

    def _handle_right_click(self, event) -> str:
        row_id = self._tree.identify_row(event.y)
        if row_id and row_id not in self._tree.selection():
            self._tree.selection_set(row_id)
            self._tree.focus(row_id)
        self._show_menu(event)
        return "break"

    def _invoke_if_set(self, cb: Optional[Callable[[List[Link]], None]]) -> str:
        if cb:
            links = self.get_selected_links()
            if links:
                cb(links)
        return "break"

    # --------------------------------------------------------------- menu

    def _show_menu(self, event) -> None:
        links = self.get_selected_links()
        if not links:
            return

        menu = tk.Menu(self._tree, tearoff=0)
        n = len(links)
        plural = "" if n == 1 else f" ({n})"

        if self._on_open:
            menu.add_command(label=f"Open{plural}", command=lambda: self._on_open(links))
        if self._on_open_in_browser:
            menu.add_command(
                label=f"Open in Browser{plural}",
                command=lambda: self._on_open_in_browser(links),
            )
        if self._on_edit and n == 1:
            menu.add_command(label="Edit…", command=lambda: self._on_edit(links[0]))
        if self._on_toggle_favorite:
            menu.add_command(
                label=f"Toggle Favorite{plural}",
                command=lambda: self._on_toggle_favorite(links),
            )
        if self._on_toggle_read:
            menu.add_command(
                label=f"Toggle Read/Unread{plural}",
                command=lambda: self._on_toggle_read(links),
            )

        # Mode-dependent destructive actions
        added_destructive = False
        if self._mode == MODE_ACTIVE and self._on_archive:
            menu.add_separator()
            menu.add_command(
                label=f"Archive{plural}",
                command=lambda: self._on_archive(links),
            )
            added_destructive = True
        if self._mode == MODE_ARCHIVED:
            if self._on_restore:
                menu.add_separator()
                menu.add_command(
                    label=f"Restore{plural}",
                    command=lambda: self._on_restore(links),
                )
                added_destructive = True
            if self._on_permanent_delete:
                if not added_destructive:
                    menu.add_separator()
                menu.add_command(
                    label=f"Delete Permanently{plural}",
                    command=lambda: self._on_permanent_delete(links),
                )
                added_destructive = True

        copy_items_added = False
        if self._on_copy_urls:
            if not copy_items_added:
                menu.add_separator()
                copy_items_added = True
            menu.add_command(label=f"Copy URL{plural}", command=lambda: self._on_copy_urls(links))
        if self._on_copy_formatted:
            if not copy_items_added:
                menu.add_separator()
                copy_items_added = True
            menu.add_command(
                label=f"Copy as Name + URL{plural}",
                command=lambda: self._on_copy_formatted(links),
            )
        if self._on_copy_markdown:
            if not copy_items_added:
                menu.add_separator()
                copy_items_added = True
            menu.add_command(
                label=f"Copy as Markdown{plural}",
                command=lambda: self._on_copy_markdown(links),
            )

        if self._on_view_stats and n == 1:
            menu.add_separator()
            menu.add_command(
                label="View Statistics",
                command=lambda: self._on_view_stats(links[0]),
            )

        # Host-defined extras (e.g. cache actions for the main view)
        if self._on_extend_menu:
            self._on_extend_menu(links, menu)

        # Don't post an empty menu
        try:
            if menu.index("end") is None:
                return
        except tk.TclError:
            return

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ----------------------------------------------------- keyboard navigation

    def _nav(self, direction: str, extend: bool = False) -> str:
        items = self._tree.get_children()
        if not items:
            return "break"

        current = self._tree.focus()
        selection = list(self._tree.selection())

        if not current or current not in items:
            target = selection[0] if (selection and selection[0] in items) else items[0]
            if extend:
                self._tree.selection_add(target)
            else:
                self._tree.selection_set(target)
            self._tree.focus(target)
            self._tree.see(target)
            return "break"

        idx = items.index(current)
        if direction == "up":
            new_idx = max(0, idx - 1)
        elif direction == "down":
            new_idx = min(len(items) - 1, idx + 1)
        elif direction == "home":
            new_idx = 0
        elif direction == "end":
            new_idx = len(items) - 1
        elif direction == "page_up":
            new_idx = max(0, idx - self._page_size())
        elif direction == "page_down":
            new_idx = min(len(items) - 1, idx + self._page_size())
        else:
            return "break"

        target = items[new_idx]
        if extend:
            if not selection:
                self._tree.selection_add(current)
            self._tree.selection_add(target)
        else:
            self._tree.selection_set(target)
        self._tree.focus(target)
        self._tree.see(target)
        return "break"

    def _nav_shift_anchor(self, edge: str) -> str:
        """Shift+Home/End: extend the selection from the focused row to the edge."""
        items = self._tree.get_children()
        if not items:
            return "break"
        current = self._tree.focus()
        if not current or current not in items:
            return self._nav(edge, extend=True)
        anchor_idx = items.index(current)
        edge_idx = 0 if edge == "home" else len(items) - 1
        lo, hi = sorted((anchor_idx, edge_idx))
        self._tree.selection_set(items[lo])
        for i in range(lo + 1, hi + 1):
            self._tree.selection_add(items[i])
        self._tree.focus(items[edge_idx])
        self._tree.see(items[edge_idx])
        return "break"

    def _page_size(self) -> int:
        try:
            first = self._tree.get_children()[0]
            bbox = self._tree.bbox(first)
            if bbox:
                row_h = bbox[3]
                visible = max(1, self._tree.winfo_height() // row_h - 1)
                return min(visible, 20)
        except (IndexError, tk.TclError):
            pass
        return 10

    # ------------------------------------------------------- callback setters

    def set_open_callback(self, cb: Callable[[List[Link]], None]) -> None:
        self._on_open = cb

    def set_open_in_browser_callback(self, cb: Callable[[List[Link]], None]) -> None:
        """Open links in the browser, bypassing any offline cache."""
        self._on_open_in_browser = cb

    def set_edit_callback(self, cb: Callable[[Link], None]) -> None:
        self._on_edit = cb

    def set_toggle_favorite_callback(self, cb: Callable[[List[Link]], None]) -> None:
        self._on_toggle_favorite = cb

    def set_toggle_read_callback(self, cb: Callable[[List[Link]], None]) -> None:
        self._on_toggle_read = cb

    def set_archive_callback(self, cb: Callable[[List[Link]], None]) -> None:
        self._on_archive = cb

    def set_restore_callback(self, cb: Callable[[List[Link]], None]) -> None:
        self._on_restore = cb

    def set_permanent_delete_callback(self, cb: Callable[[List[Link]], None]) -> None:
        self._on_permanent_delete = cb

    def set_copy_urls_callback(self, cb: Callable[[List[Link]], None]) -> None:
        self._on_copy_urls = cb

    def set_copy_formatted_callback(self, cb: Callable[[List[Link]], None]) -> None:
        self._on_copy_formatted = cb

    def set_copy_markdown_callback(self, cb: Callable[[List[Link]], None]) -> None:
        self._on_copy_markdown = cb

    def set_view_stats_callback(self, cb: Callable[[Link], None]) -> None:
        self._on_view_stats = cb

    def set_sort_callback(self, cb: Callable[[str, bool], None]) -> None:
        self._on_sort = cb

    def set_extend_menu_callback(
        self, cb: Callable[[List[Link], tk.Menu], None]
    ) -> None:
        """Host hook to append entries to the right-click menu (e.g. cache actions)."""
        self._on_extend_menu = cb

    # ----------------------------------------------------------- introspection

    @property
    def tree(self) -> ttk.Treeview:
        """Raw Treeview, exposed for the few host-specific bindings that
        need to attach extra key handlers (e.g. Cmd+C in the main window)."""
        return self._tree
