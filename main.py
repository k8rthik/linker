import json
import os
import random
import tkinter as tk
import webbrowser
from tkinter import messagebox, simpledialog

DATA_FILE = "links.json"


def load_links():
    if not os.path.exists(DATA_FILE):
        print("No data file found. Starting with an empty list.")
        return []
    with open(DATA_FILE, "r") as f:
        links = json.load(f)
    print(f"Loaded {len(links)} links from {DATA_FILE}.")
    return links


def save_links(links):
    with open(DATA_FILE, "w") as f:
        json.dump(links, f, indent=4)
    print(f"Saved {len(links)} links to {DATA_FILE}.")


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

        self.listbox = tk.Listbox(container, width=50, height=15)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(
            container, orient=tk.VERTICAL, command=self.listbox.yview
        )
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Bind double-click to open link
        self.listbox.bind("<Double-Button-1>", self._open_selected)
        # Bind Delete key to delete link
        self.listbox.bind("<Delete>", self._delete_selected)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(btn_frame, text="Mass Add Links", command=self._mass_add_links).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Edit Name", command=self._edit_name).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Toggle Favorite", command=self._toggle_fav).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Open Random", command=self._open_random).pack(
            side=tk.LEFT, padx=5
        )

    def _refresh_list(self):
        print("Refreshing list display.")
        self.listbox.delete(0, tk.END)
        for link in self.links:
            prefix = "★ " if link.get("favorite") else "  "
            self.listbox.insert(tk.END, f"{prefix}{link.get('name')}")

    def _mass_add_links(self):
        print("Opening Mass Add Links dialog.")
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Links")

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
            print(f"Mass add: found {len(lines)} lines to add.")
            for url in lines:
                print(f"Adding link: {url}")
                self.links.append({"name": url, "url": url, "favorite": False})
            save_links(self.links)
            self._refresh_list()
            dialog.destroy()

        def on_cancel():
            print("Mass add canceled.")
            dialog.destroy()

        tk.Button(btn_frame, text="OK", command=on_ok, width=10).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(
            side=tk.LEFT, padx=5
        )

        self.root.update_idletasks()
        x = (
            self.root.winfo_x()
            + (self.root.winfo_width() // 2)
            - (dialog.winfo_reqwidth() // 2)
        )
        y = (
            self.root.winfo_y()
            + (self.root.winfo_height() // 2)
            - (dialog.winfo_reqheight() // 2)
        )
        dialog.geometry(f"+{x}+{y}")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_set()

    def _edit_name(self):
        idx = self._selected_index()
        if idx is None:
            print("Edit Name: no selection.")
            return
        current = self.links[idx]["name"]
        new_name = simpledialog.askstring(
            "Edit Name", "New name:", initialvalue=current
        )
        if not new_name:
            print("Edit Name: canceled or empty input.")
            return
        print(f"Changing name from '{current}' to '{new_name}'.")
        self.links[idx]["name"] = new_name
        save_links(self.links)
        self._refresh_list()

    def _toggle_fav(self):
        idx = self._selected_index()
        if idx is None:
            print("Toggle Favorite: no selection.")
            return
        link = self.links[idx]
        link["favorite"] = not link.get("favorite", False)
        print(f"Toggling favorite for '{link['name']}' to {link['favorite']}.")
        save_links(self.links)
        self._refresh_list()

    def _open_random(self):
        print("Open Random called.")
        if not self.links:
            print("Open Random: no links available.")
            messagebox.showinfo("Info", "No links available.")
            return
        choice = random.choice(self.links)
        print(f"Randomly selected: '{choice['name']}' -> {choice['url']}")
        webbrowser.open(choice.get("url"))

    def _open_selected(self, event):
        idx = self._selected_index()
        if idx is None:
            print("Open Selected: no selection on double-click.")
            return
        link = self.links[idx]
        print(f"Opening selected link: '{link['name']}' -> {link['url']}")
        webbrowser.open(link.get("url"))

    def _delete_selected(self, event):
        idx = self._selected_index()
        if idx is None:
            print("Delete: no selection to delete.")
            return
        link = self.links[idx]
        print(f"Deleting selected link: '{link['name']}' -> {link['url']}")
        del self.links[idx]
        save_links(self.links)
        self._refresh_list()

    def _selected_index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None


if __name__ == "__main__":
    root = tk.Tk()
    app = LinkApp(root)
    root.mainloop()
