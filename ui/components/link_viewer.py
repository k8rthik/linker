"""
Reusable link viewer component with consistent formatting and context menu.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Callable
from datetime import datetime

from models.link import Link


class LinkViewerComponent:
    """Reusable component for viewing lists of links with consistent UI and actions."""

    def __init__(self, parent: tk.Widget, show_columns: Optional[List[str]] = None):
        """
        Initialize link viewer component.

        Args:
            parent: Parent widget
            show_columns: List of columns to show. Options: 'rank', 'opens', 'score',
                         'name', 'url', 'favorite', 'last_opened', 'category', 'domain',
                         'created', 'read_status'
                         Default: ['rank', 'opens', 'name', 'url']
        """
        self._parent = parent
        self._links: List[Link] = []
        self._show_columns = show_columns or ['rank', 'opens', 'name', 'url']

        # Callbacks
        self._on_open_link: Optional[Callable[[Link], None]] = None
        self._on_edit_link: Optional[Callable[[Link], None]] = None
        self._on_view_stats: Optional[Callable[[Link], None]] = None

        self._create_components()

    def _create_components(self) -> None:
        """Create the viewer components."""
        # Main frame
        self._frame = tk.Frame(self._parent)

        # Define all possible columns
        all_columns = {
            'rank': {'text': '#', 'width': 40, 'minwidth': 40},
            'opens': {'text': 'Opens', 'width': 60, 'minwidth': 50},
            'score': {'text': 'Score', 'width': 60, 'minwidth': 50},
            'name': {'text': 'Name', 'width': 300, 'minwidth': 200},
            'url': {'text': 'URL', 'width': 250, 'minwidth': 150},
            'favorite': {'text': 'Fav', 'width': 40, 'minwidth': 40},
            'last_opened': {'text': 'Last Opened', 'width': 120, 'minwidth': 100},
            'category': {'text': 'Category', 'width': 100, 'minwidth': 80},
            'domain': {'text': 'Domain', 'width': 150, 'minwidth': 100},
            'created': {'text': 'Created', 'width': 120, 'minwidth': 100},
            'read_status': {'text': 'Status', 'width': 70, 'minwidth': 60},
            'reason': {'text': 'Reason', 'width': 250, 'minwidth': 200},
            'health_status': {'text': 'Status', 'width': 80, 'minwidth': 80},
            'http_code': {'text': 'HTTP Code', 'width': 80, 'minwidth': 80}
        }

        # Filter to only shown columns
        columns = [col for col in self._show_columns if col in all_columns]

        # Create treeview
        self._tree = ttk.Treeview(self._frame, columns=columns, show="headings", height=20)

        # Configure columns
        for col in columns:
            config = all_columns[col]
            self._tree.heading(col, text=config['text'])
            self._tree.column(col, width=config['width'], minwidth=config['minwidth'])

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self._frame, orient=tk.VERTICAL, command=self._tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.config(yscrollcommand=scrollbar.set)

        # Bind events
        self._tree.bind("<Double-1>", self._on_double_click)
        self._tree.bind("<Button-2>", self._show_context_menu)  # Right-click on Mac
        self._tree.bind("<Button-3>", self._show_context_menu)  # Right-click on Windows/Linux

        # Create context menu
        self._context_menu = tk.Menu(self._tree, tearoff=0)
        self._context_menu.add_command(label="Open Link", command=self._open_selected)
        self._context_menu.add_command(label="Edit Link", command=self._edit_selected)
        self._context_menu.add_separator()
        self._context_menu.add_command(label="View Statistics", command=self._view_stats_selected)
        self._context_menu.add_command(label="Copy URL", command=self._copy_url)

    def pack(self, **kwargs) -> None:
        """Pack the frame."""
        self._frame.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        """Grid the frame."""
        self._frame.grid(**kwargs)

    def set_links(self, links: List[Link], data_getter: Optional[Callable[[Link], dict]] = None) -> None:
        """
        Set the links to display.

        Args:
            links: List of links to display
            data_getter: Optional function that takes a link and returns a dict of column values
                        If not provided, will use default data extraction
        """
        self._links = links
        self._tree.delete(*self._tree.get_children())

        for rank, link in enumerate(links, 1):
            if data_getter:
                values = data_getter(link)
            else:
                values = self._get_default_values(link, rank)

            self._tree.insert("", "end", values=values)

    def _get_default_values(self, link: Link, rank: int) -> tuple:
        """Get default column values for a link."""
        value_map = {
            'rank': rank,
            'opens': link.open_count,
            'score': 0,  # Should be provided by data_getter
            'name': link.name,
            'url': link.url,
            'favorite': "⭐" if link.favorite else "",
            'last_opened': self._format_date(link.last_opened) if link.last_opened else "Never",
            'category': link.category or "Uncategorized",
            'domain': link.domain,
            'created': self._format_date(link.date_added),
            'read_status': "Read" if not link.is_unread() else "Unread",
            'reason': "",  # Should be provided by data_getter
            'health_status': link.link_status or "unknown",
            'http_code': link.http_status_code or "N/A"
        }

        return tuple(value_map.get(col, "") for col in self._show_columns)

    def _format_date(self, date_str: Optional[str]) -> str:
        """Format ISO datetime string to readable format."""
        if not date_str:
            return "Never"
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            return "Unknown"

    def _get_selected_link(self) -> Optional[Link]:
        """Get the currently selected link."""
        selection = self._tree.selection()
        if selection:
            index = self._tree.index(selection[0])
            if 0 <= index < len(self._links):
                return self._links[index]
        return None

    def _on_double_click(self, event) -> None:
        """Handle double-click on link."""
        link = self._get_selected_link()
        if link and self._on_open_link:
            self._on_open_link(link)

    def _show_context_menu(self, event) -> None:
        """Show context menu at mouse position."""
        # Select the item under cursor
        item = self._tree.identify_row(event.y)
        if item:
            self._tree.selection_set(item)
            self._context_menu.post(event.x_root, event.y_root)

    def _open_selected(self) -> None:
        """Open the selected link."""
        link = self._get_selected_link()
        if link and self._on_open_link:
            self._on_open_link(link)

    def _edit_selected(self) -> None:
        """Edit the selected link."""
        link = self._get_selected_link()
        if link and self._on_edit_link:
            self._on_edit_link(link)
        elif link and not self._on_edit_link:
            messagebox.showinfo("Not Available", "Edit functionality not available in this context.")

    def _view_stats_selected(self) -> None:
        """View statistics for the selected link."""
        link = self._get_selected_link()
        if link and self._on_view_stats:
            self._on_view_stats(link)
        elif link and not self._on_view_stats:
            # Show simple stats messagebox
            stats = (
                f"Link Statistics\n\n"
                f"Name: {link.name}\n"
                f"URL: {link.url}\n"
                f"Opens: {link.open_count}\n"
                f"Favorite: {'Yes' if link.favorite else 'No'}\n"
                f"Status: {'Read' if not link.is_unread() else 'Unread'}\n"
                f"Domain: {link.domain}\n"
                f"Created: {self._format_date(link.date_added)}\n"
                f"Last Opened: {self._format_date(link.last_opened)}"
            )
            messagebox.showinfo("Link Statistics", stats)

    def _copy_url(self) -> None:
        """Copy the selected link's URL to clipboard."""
        link = self._get_selected_link()
        if link:
            self._parent.clipboard_clear()
            self._parent.clipboard_append(link.url)
            messagebox.showinfo("Copied", "URL copied to clipboard")

    # Callback setters
    def set_open_callback(self, callback: Callable[[Link], None]) -> None:
        """Set callback for opening links."""
        self._on_open_link = callback

    def set_edit_callback(self, callback: Callable[[Link], None]) -> None:
        """Set callback for editing links."""
        self._on_edit_link = callback

    def set_view_stats_callback(self, callback: Callable[[Link], None]) -> None:
        """Set callback for viewing link statistics."""
        self._on_view_stats = callback

    def get_frame(self) -> tk.Frame:
        """Get the main frame widget."""
        return self._frame
