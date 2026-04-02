import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Tuple


class TitleApprovalDialog:
    """Streaming approval dialog — rows appear as titles are fetched.

    Usage:
        dialog = TitleApprovalDialog(root, total=len(links))
        # From worker threads, call on main thread:
        dialog.add_change(url, current_name, new_title)
        dialog.increment_progress()       # for skipped/failed URLs too
        dialog.mark_complete()            # when all fetches done
        approved = dialog.wait()          # blocks until user closes
    """

    def __init__(self, parent: tk.Tk, total: int):
        self._parent = parent
        self._total = total
        self._fetched = 0
        self._changes: List[Tuple[str, str, str]] = []
        self._check_vars: List[tk.BooleanVar] = []
        self._approved: List[Tuple[str, str]] = []
        self._complete = False
        self._dialog: Optional[tk.Toplevel] = None

        self._create_dialog()

    # ── Dialog construction ──────────────────────────────────────────

    def _create_dialog(self) -> None:
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Force Refresh Titles")
        self._dialog.geometry("900x550")
        self._dialog.resizable(True, True)

        main_frame = ttk.Frame(self._dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._create_progress_section(main_frame)
        self._create_summary(main_frame)
        self._create_change_list(main_frame)
        self._create_buttons(main_frame)

        self._dialog.transient(self._parent)
        self._dialog.grab_set()
        self._dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _create_progress_section(self, parent: ttk.Frame) -> None:
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill=tk.X, pady=(0, 6))

        self._progress_label = ttk.Label(
            progress_frame,
            text=f"Fetching titles: 0 / {self._total}..."
        )
        self._progress_label.pack(anchor=tk.W, pady=(0, 3))

        self._progress_bar = ttk.Progressbar(
            progress_frame, maximum=self._total, mode="determinate"
        )
        self._progress_bar.pack(fill=tk.X)

    def _create_summary(self, parent: ttk.Frame) -> None:
        summary_frame = ttk.Frame(parent)
        summary_frame.pack(fill=tk.X, pady=(4, 4))

        self._summary_label = ttk.Label(
            summary_frame,
            text="Waiting for results...",
            font=("Arial", 11, "bold")
        )
        self._summary_label.pack(anchor=tk.W)

        ttk.Label(
            summary_frame,
            text="Check the ones you want to update. Unchecked links keep their current name."
        ).pack(anchor=tk.W, pady=(2, 0))

    def _create_change_list(self, parent: ttk.Frame) -> None:
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        self._scroll_frame = ttk.Frame(canvas)

        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # macOS-native mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas = canvas

        # Header
        header = ttk.Frame(self._scroll_frame)
        header.pack(fill=tk.X, padx=5, pady=(0, 4))
        ttk.Label(header, text="Current Name", font=("Arial", 10, "bold"),
                  width=38).pack(side=tk.LEFT, padx=(24, 0))
        ttk.Label(header, text="  \u2192  ", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        ttk.Label(header, text="New Title", font=("Arial", 10, "bold"),
                  width=38).pack(side=tk.LEFT)

        ttk.Separator(self._scroll_frame, orient=tk.HORIZONTAL).pack(
            fill=tk.X, padx=5, pady=2
        )

    def _create_buttons(self, parent: ttk.Frame) -> None:
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        left = ttk.Frame(btn_frame)
        left.pack(side=tk.LEFT)
        ttk.Button(left, text="Select All",
                   command=self._select_all).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(left, text="Deselect All",
                   command=self._deselect_all).pack(side=tk.LEFT)

        right = ttk.Frame(btn_frame)
        right.pack(side=tk.RIGHT)
        ttk.Button(right, text="Cancel",
                   command=self._on_cancel).pack(side=tk.RIGHT, padx=(4, 0))
        self._apply_btn = ttk.Button(right, text="Apply Selected (0)",
                                     command=self._on_apply)
        self._apply_btn.pack(side=tk.RIGHT)

    # ── Streaming API (called from main thread via root.after) ───────

    def add_change(self, url: str, current_name: str, new_title: str) -> None:
        """Add a row to the dialog. Must be called on the main thread."""
        self._changes.append((url, current_name, new_title))

        var = tk.BooleanVar(value=True)
        var.trace_add("write", lambda *_: self._update_apply_count())
        self._check_vars.append(var)

        row = ttk.Frame(self._scroll_frame)
        row.pack(fill=tk.X, padx=5, pady=1)

        ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT, padx=(0, 4))

        ttk.Label(row, text=self._truncate(current_name, 40),
                  width=38, anchor=tk.W).pack(side=tk.LEFT)
        ttk.Label(row, text="  \u2192  ").pack(side=tk.LEFT)
        ttk.Label(row, text=self._truncate(new_title, 40),
                  width=38, anchor=tk.W, foreground="green").pack(side=tk.LEFT)

        self._update_summary()
        self._update_apply_count()

    def increment_progress(self) -> None:
        """Advance the progress bar by one. Must be called on the main thread."""
        self._fetched += 1
        self._progress_bar["value"] = self._fetched
        self._progress_label.config(
            text=f"Fetching titles: {self._fetched} / {self._total}..."
        )

    def mark_complete(self) -> None:
        """Signal that all fetches are done. Must be called on the main thread."""
        self._complete = True
        self._progress_label.config(
            text=f"Done — fetched {self._total} titles."
        )
        self._progress_bar["value"] = self._total
        self._update_summary()

    # ── Internal helpers ─────────────────────────────────────────────

    def _update_summary(self) -> None:
        n = len(self._changes)
        status = "" if self._complete else " (still fetching...)"
        self._summary_label.config(
            text=f"{n} title change(s) found{status}"
        )

    def _update_apply_count(self) -> None:
        checked = sum(1 for v in self._check_vars if v.get())
        self._apply_btn.config(text=f"Apply Selected ({checked})")

    def _select_all(self) -> None:
        for var in self._check_vars:
            var.set(True)

    def _deselect_all(self) -> None:
        for var in self._check_vars:
            var.set(False)

    def _on_apply(self) -> None:
        self._approved = [
            (url, new_title)
            for (url, _current, new_title), var
            in zip(self._changes, self._check_vars)
            if var.get()
        ]
        self._cleanup_bindings()
        self._dialog.destroy()

    def _on_cancel(self) -> None:
        self._approved = []
        self._cleanup_bindings()
        self._dialog.destroy()

    def _cleanup_bindings(self) -> None:
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")

    def wait(self) -> List[Tuple[str, str]]:
        """Block until dialog closes, then return approved (url, title) pairs."""
        self._dialog.wait_window()
        return self._approved

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len - 3] + "..."
