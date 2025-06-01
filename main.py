import json
import os
import random
import webbrowser
import tkinter as tk
from tkinter import simpledialog, messagebox

DATA_FILE = "links.json"

def load_links():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_links(links):
    with open(DATA_FILE, "w") as f:
        json.dump(links, f, indent=4)

class LinkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Link Randomizer")
        self.links = load_links()
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        container = tk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.listbox = tk.Listbox(container, width=50, height=15)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(btn_frame, text="Add Link",       command=self._add_link).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Edit Name",      command=self._edit_name).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Toggle Favorite",command=self._toggle_fav).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Open Random",     command=self._open_random).pack(side=tk.LEFT, padx=5)

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for link in self.links:
            prefix = "★ " if link.get("favorite") else "  "
            self.listbox.insert(tk.END, f"{prefix}{link.get('name')}")

    def _add_link(self):
        name = simpledialog.askstring("Add Link", "Enter link name:")
        if not name:
            return
        url = simpledialog.askstring("Add Link", "Enter URL:")
        if not url:
            return
        self.links.append({"name": name, "url": url, "favorite": False})
        save_links(self.links)
        self._refresh_list()

    def _edit_name(self):
        idx = self._selected_index()
        if idx is None:
            return
        current = self.links[idx]["name"]
        new_name = simpledialog.askstring("Edit Name", "New name:", initialvalue=current)
        if not new_name:
            return
        self.links[idx]["name"] = new_name
        save_links(self.links)
        self._refresh_list()

    def _toggle_fav(self):
        idx = self._selected_index()
        if idx is None:
            return
        self.links[idx]["favorite"] = not self.links[idx].get("favorite", False)
        save_links(self.links)
        self._refresh_list()

    def _open_random(self):
        if not self.links:
            messagebox.showinfo("Info", "No links available.")
            return
        choice = random.choice(self.links)
        webbrowser.open(choice.get("url"))

    def _selected_index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None

if __name__ == "__main__":
    root = tk.Tk()
    app = LinkApp(root)
    root.mainloop()

