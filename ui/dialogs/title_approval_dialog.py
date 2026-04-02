import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Tuple


class TitleApprovalDialog:
    """Dialog for reviewing and approving title changes before applying them."""

    def __init__(self, parent: tk.Tk,
                 changes: List[Tuple[str, str, str]]):
        """
        Args:
            parent: Parent window
            changes: List of (url, current_name, new_title) tuples
        """
        self._parent = parent
        self._changes = changes
        self._dialog: Optional[tk.Toplevel] = None
        self._check_vars: List[tk.BooleanVar] = []
        self._approved: List[Tuple[str, str]] = []

        self._create_dialog()

    def _create_dialog(self) -> None:
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Review Title Changes")
        self._dialog.geometry("900x550")
        self._dialog.resizable(True, True)

        main_frame = ttk.Frame(self._dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._create_summary(main_frame)
        self._create_change_list(main_frame)
        self._create_buttons(main_frame)

        self._dialog.transient(self._parent)
        self._dialog.grab_set()

    def _create_summary(self, parent: ttk.Frame) -> None:
        summary_frame = ttk.Frame(parent)
        summary_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(
            summary_frame,
            text=f"{len(self._changes)} link(s) have different titles than what's currently shown.",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W)

        ttk.Label(
            summary_frame,
            text="Check the ones you want to update. Unchecked links keep their current name."
        ).pack(anchor=tk.W, pady=(2, 0))

    def _create_change_list(self, parent: ttk.Frame) -> None:
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Canvas + scrollbar for scrollable checkbox list
        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        self._scroll_frame = ttk.Frame(canvas)

        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        # macOS scroll events
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas = canvas

        # Header row
        header = ttk.Frame(self._scroll_frame)
        header.pack(fill=tk.X, padx=5, pady=(0, 4))
        ttk.Label(header, text="Current Name", font=("Arial", 10, "bold"), width=38).pack(side=tk.LEFT)
        ttk.Label(header, text="  →  ", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        ttk.Label(header, text="New Title", font=("Arial", 10, "bold"), width=38).pack(side=tk.LEFT)

        ttk.Separator(self._scroll_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=2)

        # One row per change
        for url, current_name, new_title in self._changes:
            var = tk.BooleanVar(value=True)
            self._check_vars.append(var)

            row = ttk.Frame(self._scroll_frame)
            row.pack(fill=tk.X, padx=5, pady=1)

            cb = ttk.Checkbutton(row, variable=var)
            cb.pack(side=tk.LEFT, padx=(0, 4))

            current_display = self._truncate(current_name, 40)
            new_display = self._truncate(new_title, 40)

            ttk.Label(row, text=current_display, width=38, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(row, text="  →  ").pack(side=tk.LEFT)
            ttk.Label(row, text=new_display, width=38, anchor=tk.W,
                      foreground="green").pack(side=tk.LEFT)

    def _create_buttons(self, parent: ttk.Frame) -> None:
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        # Left side: select/deselect all
        left = ttk.Frame(btn_frame)
        left.pack(side=tk.LEFT)
        ttk.Button(left, text="Select All", command=self._select_all).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(left, text="Deselect All", command=self._deselect_all).pack(side=tk.LEFT)

        # Right side: apply/cancel
        right = ttk.Frame(btn_frame)
        right.pack(side=tk.RIGHT)
        ttk.Button(right, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(right, text="Apply Selected", command=self._on_apply).pack(side=tk.RIGHT)

    def _select_all(self) -> None:
        for var in self._check_vars:
            var.set(True)

    def _deselect_all(self) -> None:
        for var in self._check_vars:
            var.set(False)

    def _on_apply(self) -> None:
        self._approved = [
            (url, new_title)
            for (url, _current, new_title), var in zip(self._changes, self._check_vars)
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

    def get_approved(self) -> List[Tuple[str, str]]:
        """Return list of (url, new_title) tuples the user approved."""
        return self._approved

    def wait(self) -> List[Tuple[str, str]]:
        """Block until dialog closes, then return approved changes."""
        self._dialog.wait_window()
        return self._approved

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len - 3] + "..."
