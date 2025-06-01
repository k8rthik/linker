import tkinter as tk
from typing import Callable, List


class AddLinksDialog:
    """Dialog for adding multiple links at once."""
    
    def __init__(self, parent: tk.Tk, on_add: Callable[[List[str]], None]):
        self._parent = parent
        self._on_add = on_add
        self._dialog = None
        self._create_dialog()
    
    def _create_dialog(self) -> None:
        """Create and show the add links dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Add Links")
        self._dialog.geometry("400x300")
        
        # Instructions
        tk.Label(self._dialog, text="Paste one URL per line:").pack(padx=10, pady=(10, 0))
        
        # Text area with scrollbar
        text_frame = tk.Frame(self._dialog)
        text_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        self._text_widget = tk.Text(text_frame, width=50, height=10)
        self._text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self._text_widget.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self._text_widget.config(yscrollcommand=scrollbar.set)
        
        # Buttons
        btn_frame = tk.Frame(self._dialog)
        btn_frame.pack(pady=(0, 10))
        
        ok_btn = tk.Button(btn_frame, text="OK", command=self._on_ok_clicked, width=10)
        ok_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="Cancel", command=self._on_cancel_clicked, width=10)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Configure dialog
        self._configure_dialog()
    
    def _configure_dialog(self) -> None:
        """Configure dialog properties."""
        self._dialog.transient(self._parent)
        self._dialog.grab_set()
        self._text_widget.focus_set()
    
    def _on_ok_clicked(self) -> None:
        """Handle OK button click."""
        raw_text = self._text_widget.get("1.0", tk.END).strip()
        urls = [line.strip() for line in raw_text.splitlines() if line.strip()]
        
        if urls:
            self._on_add(urls)
        
        self._dialog.destroy()
    
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        self._dialog.destroy() 