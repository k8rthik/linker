"""
Dialog for displaying scraper status and progress.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime


class ScraperStatusDialog:
    """Dialog for showing real-time scraper status and progress."""

    def __init__(self, parent: tk.Tk):
        self._parent = parent
        self._dialog = None
        self._status_label = None
        self._progress_label = None
        self._details_text = None
        self._progress_bar = None
        self._is_active = False
        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create and show the scraper status dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Web Scraper Status")
        self._dialog.geometry("500x400")

        # Main frame
        main_frame = tk.Frame(self._dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(main_frame, text="Web Scraper", font=("", 16, "bold"))
        title_label.pack(pady=(0, 10))

        # Status indicator
        status_frame = tk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=10)

        tk.Label(status_frame, text="Status:", font=("", 11, "bold")).pack(side=tk.LEFT)
        self._status_label = tk.Label(status_frame, text="Idle", font=("", 11),
                                      fg="#666666")
        self._status_label.pack(side=tk.LEFT, padx=10)

        # Progress bar
        self._progress_bar = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
        self._progress_bar.pack(fill=tk.X, pady=10)

        # Progress details
        self._progress_label = tk.Label(main_frame, text="", font=("", 10))
        self._progress_label.pack(pady=5)

        # Details text area
        details_frame = tk.LabelFrame(main_frame, text="Scraping Details", padx=10, pady=10)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Scrollable text widget
        text_scroll = tk.Scrollbar(details_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._details_text = tk.Text(details_frame, height=10, wrap=tk.WORD,
                                     yscrollcommand=text_scroll.set,
                                     font=("Courier", 9))
        self._details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.config(command=self._details_text.yview)

        # Buttons
        btn_frame = tk.Frame(self._dialog)
        btn_frame.pack(pady=(0, 10))

        self._close_btn = tk.Button(btn_frame, text="Close", command=self._dialog.destroy, width=10)
        self._close_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Clear Log", command=self._clear_log, width=10).pack(side=tk.LEFT, padx=5)

        # Configure dialog
        self._dialog.transient(self._parent)
        # Don't grab_set() - allow interaction with main window

    def update_status(self, status: str, color: str = "#666666") -> None:
        """Update the status label."""
        if self._status_label:
            self._status_label.config(text=status, fg=color)

    def update_progress(self, message: str) -> None:
        """Update the progress message."""
        if self._progress_label:
            self._progress_label.config(text=message)

    def add_log(self, message: str, prefix: str = "•") -> None:
        """Add a log message to the details area."""
        if self._details_text:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {prefix} {message}\n"
            self._details_text.insert(tk.END, log_entry)
            self._details_text.see(tk.END)  # Auto-scroll to bottom

    def start_scraping(self, domain: str) -> None:
        """Indicate scraping has started."""
        self._is_active = True
        self.update_status("Scraping...", "#0066cc")
        self.update_progress(f"Scraping {domain}")
        self._progress_bar.start(10)
        self.add_log(f"Started scraping {domain}", "▶")

    def stop_scraping(self, success: bool = True) -> None:
        """Indicate scraping has finished."""
        self._is_active = False
        self._progress_bar.stop()
        if success:
            self.update_status("Completed", "#00aa00")
            self.update_progress("")
        else:
            self.update_status("Failed", "#cc0000")
            self.update_progress("")

    def scraping_complete(self, urls_found: int, links_added: int, duplicates: int) -> None:
        """Show scraping completion summary."""
        self.stop_scraping(success=True)
        self.add_log(f"Found {urls_found} URLs", "✓")
        self.add_log(f"Added {links_added} new links", "✓")
        if duplicates > 0:
            self.add_log(f"Skipped {duplicates} duplicates", "→")
        self.add_log("Scraping complete!", "✓")

    def scraping_error(self, error_message: str) -> None:
        """Show scraping error."""
        self.stop_scraping(success=False)
        self.add_log(f"Error: {error_message}", "✗")

    def _clear_log(self) -> None:
        """Clear the details log."""
        if self._details_text:
            self._details_text.delete("1.0", tk.END)

    def is_active(self) -> bool:
        """Check if scraper is currently active."""
        return self._is_active

    def destroy(self) -> None:
        """Destroy the dialog."""
        if self._dialog:
            self._dialog.destroy()
