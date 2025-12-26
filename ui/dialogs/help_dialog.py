"""
Dialog for displaying keyboard shortcuts and help information.
"""

import tkinter as tk
from tkinter import ttk


class HelpDialog:
    """Dialog for showing keyboard shortcuts and help."""

    def __init__(self, parent: tk.Tk):
        self._parent = parent
        self._dialog = None
        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create and show the help dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Help - Keyboard Shortcuts")
        self._dialog.geometry("700x600")

        # Create notebook for tabs
        notebook = ttk.Notebook(self._dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Shortcuts tab
        shortcuts_tab = tk.Frame(notebook)
        notebook.add(shortcuts_tab, text="Keyboard Shortcuts")
        self._create_shortcuts_view(shortcuts_tab)

        # About tab
        about_tab = tk.Frame(notebook)
        notebook.add(about_tab, text="About")
        self._create_about_view(about_tab)

        # Close button
        btn_frame = tk.Frame(self._dialog)
        btn_frame.pack(pady=(0, 10))
        tk.Button(btn_frame, text="Close", command=self._dialog.destroy, width=10).pack()

        # Configure dialog
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

    def _create_shortcuts_view(self, parent: tk.Frame) -> None:
        """Create keyboard shortcuts display."""
        # Create scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Vim-style commands
        vim_frame = tk.LabelFrame(scrollable_frame, text="Vim-Style Commands (Single Keys)",
                                  padx=15, pady=10, font=("", 11, "bold"))
        vim_frame.pack(fill=tk.X, padx=10, pady=10)

        vim_shortcuts = [
            ("f", "Toggle favorite on selected link(s)"),
            ("r", "Toggle read/unread status"),
            ("o", "Open random link"),
            ("O (Shift+o)", "Open random favorite link"),
            ("u", "Open random unread link"),
            ("d", "Delete selected link(s)"),
            ("e", "Edit selected link"),
            ("a or n", "Add new links"),
            ("p", "Manage profiles"),
            ("t", "Scan and fetch titles"),
            ("z", "Undo last delete"),
            ("l", "Focus link list"),
            ("/", "Focus search bar"),
            ("?", "Show this help dialog"),
            ("S (Shift+s)", "Toggle scraper pause/resume"),
        ]

        for key, description in vim_shortcuts:
            self._add_shortcut_row(vim_frame, key, description)

        # Numeric multipliers
        multiplier_frame = tk.LabelFrame(scrollable_frame, text="Numeric Multipliers",
                                         padx=15, pady=10, font=("", 11, "bold"))
        multiplier_frame.pack(fill=tk.X, padx=10, pady=10)

        multiplier_text = tk.Text(multiplier_frame, height=5, wrap=tk.WORD,
                                  relief=tk.FLAT, bg="#f0f0f0")
        multiplier_text.insert("1.0",
            "Type numbers (0-9) before commands to repeat them:\n\n"
            "Examples:\n"
            "  5o  → Open 5 random links\n"
            "  3f  → Toggle favorite on 3 links\n"
            "  10r → Toggle read/unread on 10 links\n\n"
            "Visual feedback: [N] shown in bottom left\n"
            "Press Escape to clear buffer without executing"
        )
        multiplier_text.configure(state='disabled')
        multiplier_text.pack(fill=tk.X)

        # Platform-independent
        platform_frame = tk.LabelFrame(scrollable_frame, text="Platform-Independent",
                                       padx=15, pady=10, font=("", 11, "bold"))
        platform_frame.pack(fill=tk.X, padx=10, pady=10)

        platform_shortcuts = [
            ("Enter", "Edit selected link"),
            ("Space", "Open selected link(s) in browser"),
            ("Delete", "Delete selected link(s)"),
            ("Tab", "Navigate between widgets"),
            ("Arrow Keys", "Navigate up/down in link list"),
            ("Escape", "Clear numeric buffer / Clear search / Clear selection"),
        ]

        for key, description in platform_shortcuts:
            self._add_shortcut_row(platform_frame, key, description)

        # Mouse shortcuts
        mouse_frame = tk.LabelFrame(scrollable_frame, text="Mouse Shortcuts",
                                    padx=15, pady=10, font=("", 11, "bold"))
        mouse_frame.pack(fill=tk.X, padx=10, pady=10)

        mouse_shortcuts = [
            ("Double-click link", "Open link in browser"),
            ("Click column header", "Sort by that column"),
        ]

        for key, description in mouse_shortcuts:
            self._add_shortcut_row(mouse_frame, key, description)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _add_shortcut_row(self, parent: tk.Frame, key: str, description: str) -> None:
        """Add a single shortcut row."""
        row = tk.Frame(parent)
        row.pack(fill=tk.X, pady=2)

        # Key label (fixed width, monospace)
        key_label = tk.Label(row, text=key, font=("Courier", 11, "bold"),
                            width=20, anchor="w", fg="#0066cc")
        key_label.pack(side=tk.LEFT)

        # Description label
        desc_label = tk.Label(row, text=description, font=("", 10), anchor="w")
        desc_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _create_about_view(self, parent: tk.Frame) -> None:
        """Create about information display."""
        about_frame = tk.Frame(parent, padx=20, pady=20)
        about_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(about_frame, text="linker",
                              font=("", 24, "bold"))
        title_label.pack(pady=(0, 10))

        # Version (read from __version__.py)
        try:
            from __version__ import __version__
            version_text = f"Version {__version__}"
        except ImportError:
            version_text = "Version unknown"

        version_label = tk.Label(about_frame, text=version_text,
                                font=("", 12))
        version_label.pack(pady=(0, 20))

        # Description
        description = (
            "A desktop link manager with profile support,\n"
            "vim-style keyboard shortcuts, and automatic\n"
            "web scraping for keeping your bookmarks up to date.\n\n"
            "Features:\n"
            "• Profile management with isolated link collections\n"
            "• Vim-style keyboard shortcuts for fast navigation\n"
            "• Automatic page title fetching\n"
            "• Background web scraping (fyptt.to) with pause/resume\n"
            "• Link analytics and statistics\n"
            "• Import/export functionality\n"
            "• Soft delete with archive (view & restore deleted links)\n"
            "• Undo delete (last 20 operations)\n"
        )

        desc_label = tk.Label(about_frame, text=description,
                             font=("", 11), justify=tk.LEFT)
        desc_label.pack(pady=10)

        # Architecture
        arch_label = tk.Label(about_frame,
                             text="Built with Python, Tkinter, BeautifulSoup4, and requests",
                             font=("", 9), fg="#666666")
        arch_label.pack(pady=(20, 0))
