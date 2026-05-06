"""Cache management dialog: shows total cache size and offers a clear-all action."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from utils.size_formatter import format_size_bytes

if TYPE_CHECKING:
    from services.cache_service import CacheService


class CacheDialog:
    def __init__(self, parent: tk.Tk, cache_service: "CacheService") -> None:
        self._parent = parent
        self._cache_service = cache_service
        self._dialog = tk.Toplevel(parent)
        self._dialog.title("Offline Cache")
        self._dialog.geometry("420x220")
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._build_ui()
        self._refresh_stats()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self._dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="Favorited links are cached for offline playback.",
            wraplength=380,
        ).pack(anchor="w", pady=(0, 12))

        self._size_label = ttk.Label(frame, text="", font=("TkDefaultFont", 12, "bold"))
        self._size_label.pack(anchor="w")

        self._count_label = ttk.Label(frame, text="")
        self._count_label.pack(anchor="w", pady=(2, 0))

        self._location_label = ttk.Label(
            frame,
            text=f"Location: {self._cache_service.cache_dir}",
            foreground="#555",
            wraplength=380,
        )
        self._location_label.pack(anchor="w", pady=(8, 16))

        if not self._cache_service.is_downloader_available():
            ttk.Label(
                frame,
                text="⚠ yt-dlp not found on PATH. Install with: brew install yt-dlp",
                foreground="#a33",
                wraplength=380,
            ).pack(anchor="w", pady=(0, 12))

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(
            button_frame, text="Clear cache", command=self._on_clear_clicked
        ).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Close", command=self._dialog.destroy).pack(
            side=tk.RIGHT
        )

    def _refresh_stats(self) -> None:
        total_bytes = self._cache_service.total_size_bytes()
        file_count = sum(
            1 for _ in self._cache_service.cache_dir.iterdir() if _.is_file()
        )
        self._size_label.config(text=format_size_bytes(total_bytes))
        self._count_label.config(
            text=f"{file_count} file{'s' if file_count != 1 else ''} cached"
        )

    def _on_clear_clicked(self) -> None:
        if not messagebox.askyesno(
            "Clear cache",
            "Delete all cached video files? Links stay in your library; only the "
            "offline copies are removed.",
            parent=self._dialog,
        ):
            return
        self._cache_service.clear_all()
        self._refresh_stats()
        messagebox.showinfo(
            "Cache cleared", "All cached videos have been removed.", parent=self._dialog
        )
