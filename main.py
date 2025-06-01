import json
import os
import random
import sys
import subprocess
import tkinter as tk
import webbrowser
from tkinter import messagebox, simpledialog

DATA_FILE = "links.json"


def load_links():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_links(links):
    with open(DATA_FILE, "w") as f:
        json.dump(links, f, indent=4)


def open_in_browser(url):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Try webbrowser first
    if webbrowser.open_new_tab(url):
        return

    # Fallback to OS-specific commands
    try:
        if sys.platform == "darwin":
            subprocess.check_call(["open", url])
        elif sys.platform.startswith("linux"):
            subprocess.check_call(["xdg-open", url])
        elif sys.platform.startswith("win"):
            subprocess.check_call(["start", url])
    except Exception:
        messagebox.showerror("Error", f"Could not open URL: {url}")


class LinkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("linker")
        self.links = load_links()
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        container = tk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.listbox = tk.Listbox(container, width=50, height=15, selectmode=tk.EXTENDED)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Bind double-click to open link and Delete key to delete link
        self.listbox.bind("<Double-Button-1>", self._open_selected)
        self.listbox.bind("<BackSpace>", self._delete_selected)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        buttons = [
            ("Mass Add Links", self._mass_add_links),
            ("Edit Name", self._edit_name),
            ("Toggle Favorite", self._toggle_fav),
            ("Open Random", self._open_random)
        ]
        
        for text, command in buttons:
            tk.Button(btn_frame, text=text, command=command).pack(side=tk.LEFT, padx=5)

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for link in self.links:
            prefix = "★ " if link.get("favorite") else "  "
            name = link.get('name')
            url = link.get('url')
            
            display_text = f"{prefix}{name}" if name == url else f"{prefix}{name} ({url})"
            self.listbox.insert(tk.END, display_text)

    def _mass_add_links(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Links")
        dialog.geometry("400x300")

        tk.Label(dialog, text="Paste one URL per line:").pack(padx=10, pady=(10, 0))

        text_frame = tk.Frame(dialog)
        text_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, width=50, height=10)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scroll = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        scroll.pack(side=tk.LEFT, fill=tk.Y)
        text_widget.config(yscrollcommand=scroll.set)

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=(0, 10))

        def on_ok():
            raw = text_widget.get("1.0", tk.END).strip()
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            for url in lines:
                self.links.append({"name": url, "url": url, "favorite": False})
            save_links(self.links)
            self._refresh_list()
            dialog.destroy()

        tk.Button(btn_frame, text="OK", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)

        # Center dialog on parent
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_set()

    def _edit_name(self):
        indices = self._selected_indices()
        if not indices:
            return
        if len(indices) > 1:
            messagebox.showinfo("Info", "Please select only one item to edit its name.")
            return
        
        idx = indices[0]
        current = self.links[idx]["name"]
        new_name = simpledialog.askstring("Edit Name", "New name:", initialvalue=current)
        if new_name:
            self.links[idx]["name"] = new_name
            save_links(self.links)
            self._refresh_list()

    def _toggle_fav(self):
        indices = self._selected_indices()
        if not indices:
            return
        
        for idx in indices:
            link = self.links[idx]
            link["favorite"] = not link.get("favorite", False)
        
        save_links(self.links)
        self._refresh_list()

    def _open_random(self):
        if not self.links:
            messagebox.showinfo("Info", "No links available.")
            return

        choice = random.choice(self.links)
        open_in_browser(choice["url"])

    def _open_selected(self, event):
        indices = self._selected_indices()
        if not indices:
            return

        for idx in indices:
            open_in_browser(self.links[idx]["url"])

    def _delete_selected(self, event):
        indices = self._selected_indices()
        if not indices:
            return
        
        if len(indices) > 1:
            if not messagebox.askyesno("Confirm Deletion", 
                                     f"Are you sure you want to delete {len(indices)} selected link(s)?"):
                return
        
        # Delete from highest index to lowest to avoid index shifting issues
        for idx in sorted(indices, reverse=True):
            del self.links[idx]
        
        save_links(self.links)
        self._refresh_list()

    def _selected_indices(self):
        """Returns a list of all selected indices"""
        return list(self.listbox.curselection())


if __name__ == "__main__":
    root = tk.Tk()
    app = LinkApp(root)
    root.mainloop()
