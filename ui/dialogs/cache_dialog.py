"""Cache management dialog: shows total cache size, in-flight job, and a live log."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Optional

from utils.size_formatter import format_size_bytes

if TYPE_CHECKING:
    from services.cache_service import CacheLogEntry, CacheService


_LEVEL_COLORS = {
    "info": "#333",
    "success": "#1a7f37",
    "warn": "#9a6700",
    "error": "#cf222e",
}


class CacheDialog:
    def __init__(self, parent: tk.Tk, cache_service: "CacheService") -> None:
        self._parent = parent
        self._cache_service = cache_service
        self._dialog = tk.Toplevel(parent)
        self._dialog.title("Offline Cache")
        self._dialog.geometry("680x520")
        self._dialog.transient(parent)
        # Non-modal so the user can keep using the app while watching downloads.

        self._refresh_job: Optional[str] = None
        self._last_log_count = 0

        self._build_ui()
        self._refresh_stats()
        self._load_existing_log()
        self._schedule_refresh()

        self._dialog.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self._dialog, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="Favorited links are cached for offline playback.",
            wraplength=640,
        ).pack(anchor="w", pady=(0, 8))

        # ---- Stats row ----
        stats_frame = ttk.Frame(frame)
        stats_frame.pack(fill=tk.X, pady=(0, 8))

        self._size_label = ttk.Label(
            stats_frame, text="", font=("TkDefaultFont", 12, "bold")
        )
        self._size_label.pack(anchor="w")

        self._count_label = ttk.Label(stats_frame, text="")
        self._count_label.pack(anchor="w", pady=(2, 0))

        self._location_label = ttk.Label(
            stats_frame,
            text=f"Location: {self._cache_service.cache_dir}",
            foreground="#555",
            wraplength=640,
        )
        self._location_label.pack(anchor="w", pady=(4, 0))

        if not self._cache_service.is_downloader_available():
            ttk.Label(
                frame,
                text="⚠ yt-dlp not found on PATH. Install with: brew install yt-dlp",
                foreground="#a33",
                wraplength=640,
            ).pack(anchor="w", pady=(4, 8))

        # ---- Queue status ----
        queue_frame = ttk.LabelFrame(frame, text="Queue", padding=8)
        queue_frame.pack(fill=tk.X, pady=(4, 8))

        self._current_label = ttk.Label(
            queue_frame, text="Idle", wraplength=620, justify="left"
        )
        self._current_label.pack(anchor="w")

        self._queue_label = ttk.Label(queue_frame, text="0 waiting", foreground="#555")
        self._queue_label.pack(anchor="w", pady=(2, 0))

        # ---- Log ----
        log_frame = ttk.LabelFrame(frame, text="Activity log", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        text_scroll = ttk.Scrollbar(log_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._log_text = tk.Text(
            log_frame,
            height=10,
            wrap=tk.WORD,
            yscrollcommand=text_scroll.set,
            font=("Menlo", 10),
            state=tk.DISABLED,
        )
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.config(command=self._log_text.yview)

        for level, color in _LEVEL_COLORS.items():
            self._log_text.tag_configure(level, foreground=color)

        # ---- Buttons ----
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(
            button_frame, text="Clear cache", command=self._on_clear_clicked
        ).pack(side=tk.LEFT)
        ttk.Button(
            button_frame, text="Clear log", command=self._on_clear_log_clicked
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_frame, text="Close", command=self._on_close).pack(
            side=tk.RIGHT
        )

    # ---- Refresh loop ----

    def _schedule_refresh(self) -> None:
        self._refresh_job = self._dialog.after(750, self._tick)

    def _tick(self) -> None:
        if not self._dialog.winfo_exists():
            return
        self._refresh_stats()
        self._refresh_queue()
        self._append_new_log_entries()
        self._schedule_refresh()

    def _refresh_stats(self) -> None:
        total_bytes = self._cache_service.total_size_bytes()
        try:
            file_count = sum(
                1 for entry in self._cache_service.cache_dir.iterdir() if entry.is_file()
            )
        except OSError:
            file_count = 0
        self._size_label.config(text=format_size_bytes(total_bytes))
        self._count_label.config(
            text=f"{file_count} file{'s' if file_count != 1 else ''} cached"
        )

    def _refresh_queue(self) -> None:
        current = self._cache_service.current_job()
        if current is None:
            self._current_label.config(
                text="Idle — no download in progress", foreground="#555"
            )
        else:
            profile_name, link_name, link_url = current
            self._current_label.config(
                text=f"⏬ Downloading: {link_name}\n    {link_url}\n    profile: {profile_name}",
                foreground="#0a5",
            )
        pending = self._cache_service.queue_size()
        self._queue_label.config(
            text=f"{pending} waiting in queue"
        )

    def _load_existing_log(self) -> None:
        entries = self._cache_service.get_log_entries()
        for entry in entries:
            self._write_entry(entry)
        self._last_log_count = len(entries)

    def _append_new_log_entries(self) -> None:
        entries = self._cache_service.get_log_entries()
        if len(entries) < self._last_log_count:
            # Log was cleared externally — rebuild.
            self._log_text.config(state=tk.NORMAL)
            self._log_text.delete("1.0", tk.END)
            self._log_text.config(state=tk.DISABLED)
            self._last_log_count = 0
        for entry in entries[self._last_log_count :]:
            self._write_entry(entry)
        self._last_log_count = len(entries)

    def _write_entry(self, entry: "CacheLogEntry") -> None:
        ts = datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S")
        link_part = ""
        if entry.link_name:
            link_part = f" — {entry.link_name}"
        elif entry.link_url:
            link_part = f" — {entry.link_url}"
        line = f"[{ts}] {entry.event:<11} {entry.message}{link_part}\n"
        self._log_text.config(state=tk.NORMAL)
        self._log_text.insert(tk.END, line, entry.level)
        self._log_text.see(tk.END)
        self._log_text.config(state=tk.DISABLED)

    # ---- Button handlers ----

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

    def _on_clear_log_clicked(self) -> None:
        self._cache_service.clear_log()
        self._log_text.config(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)
        self._log_text.config(state=tk.DISABLED)
        self._last_log_count = 0

    def _on_close(self) -> None:
        if self._refresh_job is not None:
            try:
                self._dialog.after_cancel(self._refresh_job)
            except tk.TclError:
                pass
            self._refresh_job = None
        self._dialog.destroy()
