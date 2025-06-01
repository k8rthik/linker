import json
import os
import random
import sys
import subprocess
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk

DATA_FILE = "links.json"


def load_links():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        links = json.load(f)
    
    # Add missing fields for backward compatibility
    for link in links:
        if "date_added" not in link:
            link["date_added"] = datetime.now().isoformat()
        if "last_opened" not in link:
            link["last_opened"] = None
    
    return links


def save_links(links):
    with open(DATA_FILE, "w") as f:
        json.dump(links, f, indent=4)


def open_in_browser(url):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Try webbrowser first
    if webbrowser.open_new_tab(url):
        return True

    # Fallback to OS-specific commands
    try:
        if sys.platform == "darwin":
            subprocess.check_call(["open", url])
        elif sys.platform.startswith("linux"):
            subprocess.check_call(["xdg-open", url])
        elif sys.platform.startswith("win"):
            subprocess.check_call(["start", url])
        return True
    except Exception:
        messagebox.showerror("Error", f"Could not open URL: {url}")
        return False


def format_date(date_str):
    """Format datetime string for display"""
    if not date_str:
        return "Never"
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return "Invalid"


class LinkApp:
    def __init__(self, root):
        self.root = root
        
        # Set custom window title and properties
        self.root.title("Linker - Link Manager")
        
        # Try to set custom icon (with fallback if file doesn't exist)
        try:
            # For .ico files (Windows primarily, but works on other platforms)
            self.root.iconbitmap("assets/linker_icon.ico")
        except (tk.TclError, FileNotFoundError):
            try:
                # For .png files (cross-platform alternative)
                icon_image = tk.PhotoImage(file="assets/linker_icon.png")
                self.root.iconphoto(True, icon_image)
            except (tk.TclError, FileNotFoundError):
                # Fallback: no custom icon, use system default
                pass
        
        # Set minimum window size for better UX
        self.root.minsize(800, 500)
        
        # Set initial window size
        self.root.geometry("1000x600")
        
        # Center the window on screen
        self._center_window()
        
        self.links = load_links()
        self.filtered_links = self.links.copy()  # For search functionality
        self.sort_column = None
        self.sort_reverse = False
        self._build_ui()
        self._refresh_list()

    def _center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _build_ui(self):
        container = tk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Search frame
        self.search_frame = tk.Frame(container)
        self.search_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(self.search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self.search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Bind search as user types
        self.search_var.trace('w', self._on_search_change)
        
        # Clear search button
        self.clear_btn = tk.Button(self.search_frame, text="Clear", command=self._clear_search)
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Result count label
        self.result_label = tk.Label(self.search_frame, text="")
        self.result_label.pack(side=tk.LEFT, padx=(10, 0))

        # Create Treeview with columns
        columns = ("name", "url", "date_added", "last_opened")
        self.tree = ttk.Treeview(container, columns=columns, show="tree headings", selectmode="extended")
        
        # Configure columns
        self.tree.heading("#0", text="Fav")
        self.tree.column("#0", width=40, minwidth=40)
        
        self.tree.heading("name", text="Name")
        self.tree.column("name", width=200, minwidth=150)
        
        self.tree.heading("url", text="URL")
        self.tree.column("url", width=300, minwidth=200)
        
        self.tree.heading("date_added", text="Date Added")
        self.tree.column("date_added", width=130, minwidth=130)
        
        self.tree.heading("last_opened", text="Last Opened")
        self.tree.column("last_opened", width=130, minwidth=130)
        
        # Bind column header clicks for sorting
        self.tree.heading("#0", command=lambda: self._sort_column("favorite"))
        self.tree.heading("name", command=lambda: self._sort_column("name"))
        self.tree.heading("url", command=lambda: self._sort_column("url"))
        self.tree.heading("date_added", command=lambda: self._sort_column("date_added"))
        self.tree.heading("last_opened", command=lambda: self._sort_column("last_opened"))
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)

        # Bind double-click to open link and Delete key to delete link
        self.tree.bind("<Double-Button-1>", self._open_selected)
        self.tree.bind("<BackSpace>", self._delete_selected)

        # Bind Escape key to deselect all and clear search
        self.root.bind("<Escape>", self._on_escape)
        
        # Bind Ctrl+f/Cmd+f to focus search
        if sys.platform == "darwin":
            self.root.bind("<Command-f>", self._focus_search)
        else:
            self.root.bind("<Control-f>", self._focus_search)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        buttons = [
            ("Add Links", self._mass_add_links),
            ("Edit Name", self._edit_name),
            ("Toggle Favorite", self._toggle_fav),
            ("Mark Read/Unread", self._toggle_read_status),
            ("Open Random", self._open_random),
            ("Open Unread", self._open_random_unread)
        ]
        
        for text, command in buttons:
            tk.Button(btn_frame, text=text, command=command).pack(side=tk.LEFT, padx=5)

    def _focus_search(self, event=None):
        """Focus the search entry when Ctrl+f/Cmd+f is pressed"""
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)
        return "break"  # Prevent default behavior

    def _on_escape(self, event):
        """Handle Escape key - clear search if search has text, otherwise deselect all"""
        if self.search_var.get():
            self._clear_search()
        else:
            self._deselect_all(event)

    def _on_search_change(self, *args):
        """Called when search text changes"""
        search_term = self.search_var.get().lower().strip()
        
        if not search_term:
            self.filtered_links = self.links.copy()
        else:
            self.filtered_links = []
            for link in self.links:
                name = link.get('name', '').lower()
                url = link.get('url', '').lower()
                if search_term in name or search_term in url:
                    self.filtered_links.append(link)
        
        self._refresh_list()
        self._update_result_count()

    def _clear_search(self):
        """Clear the search and show all links"""
        self.search_var.set("")
        self.search_entry.focus_set()

    def _update_result_count(self):
        """Update the result count label"""
        total = len(self.links)
        filtered = len(self.filtered_links)
        
        if self.search_var.get().strip():
            self.result_label.config(text=f"Showing {filtered} of {total} links")
        else:
            self.result_label.config(text=f"{total} links")

    def _refresh_list(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Use filtered_links instead of self.links for display
        for i, link in enumerate(self.filtered_links):
            favorite_icon = "★" if link.get("favorite") else ""
            name = link.get('name', '')
            url = link.get('url', '')
            date_added = format_date(link.get('date_added'))
            last_opened = format_date(link.get('last_opened'))
            
            # Use the original index from self.links for proper mapping
            original_index = self.links.index(link)
            self.tree.insert("", "end", iid=str(original_index), text=favorite_icon, 
                           values=(name, url, date_added, last_opened))
        
        # Update result count
        self._update_result_count()

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
            current_time = datetime.now().isoformat()
            for url in lines:
                self.links.append({
                    "name": url, 
                    "url": url, 
                    "favorite": False,
                    "date_added": current_time,
                    "last_opened": None
                })
            save_links(self.links)
            # Update filtered links after adding new ones
            self._on_search_change()
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
            # Restore selection
            self._restore_selection(indices)

    def _toggle_fav(self):
        indices = self._selected_indices()
        if not indices:
            return
        
        for idx in indices:
            link = self.links[idx]
            link["favorite"] = not link.get("favorite", False)
        
        save_links(self.links)
        self._refresh_list()
        # Restore selection
        self._restore_selection(indices)

    def _toggle_read_status(self):
        indices = self._selected_indices()
        if not indices:
            return
        
        # Check if all selected items are unread (last_opened is None)
        selected_links = [self.links[idx] for idx in indices]
        all_unread = all(link.get("last_opened") is None for link in selected_links)
        
        current_time = datetime.now().isoformat()
        
        for idx in indices:
            link = self.links[idx]
            if all_unread:
                # If all are unread, mark them as read
                link["last_opened"] = current_time
            else:
                # If any are read or mixed, mark all as unread
                link["last_opened"] = None
        
        save_links(self.links)
        self._refresh_list()
        # Restore selection
        self._restore_selection(indices)

    def _restore_selection(self, indices):
        """Restore selection to the given indices after a refresh"""
        for idx in indices:
            if idx < len(self.links):  # Make sure index is still valid
                item_id = str(idx)
                self.tree.selection_add(item_id)

    def _open_random(self):
        if not self.links:
            messagebox.showinfo("Info", "No links available.")
            return

        choice = random.choice(self.links)
        if open_in_browser(choice["url"]):
            choice["last_opened"] = datetime.now().isoformat()
            save_links(self.links)
            
            # Find the index of the opened link
            opened_index = self.links.index(choice)
            
            # Update filtered links to reflect changes
            self._on_search_change()
            
            # Select and scroll to the opened link if it's visible in filtered results
            if choice in self.filtered_links:
                item_id = str(opened_index)
                self.tree.selection_set(item_id)
                self.tree.see(item_id)

    def _open_random_unread(self):
        # Filter links that have never been opened (last_opened is null)
        unread_links = [link for link in self.links if link.get("last_opened") is None]
        
        if not unread_links:
            messagebox.showinfo("Info", "No unread links available.")
            return

        choice = random.choice(unread_links)
        if open_in_browser(choice["url"]):
            choice["last_opened"] = datetime.now().isoformat()
            save_links(self.links)
            
            # Find the index of the opened link in the main links list
            opened_index = self.links.index(choice)
            
            # Update filtered links to reflect changes
            self._on_search_change()
            
            # Select and scroll to the opened link if it's visible in filtered results
            if choice in self.filtered_links:
                item_id = str(opened_index)
                self.tree.selection_set(item_id)
                self.tree.see(item_id)

    def _open_selected(self, event):
        indices = self._selected_indices()
        if not indices:
            return

        current_time = datetime.now().isoformat()
        for idx in indices:
            if open_in_browser(self.links[idx]["url"]):
                self.links[idx]["last_opened"] = current_time
        
        save_links(self.links)
        self._refresh_list()

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
        """Returns a list of all selected indices (in original links array)"""
        selected_items = self.tree.selection()
        return [int(item) for item in selected_items]

    def _sort_column(self, column):
        """Sort the links by the specified column"""
        # Toggle sort direction if clicking the same column
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        
        # Sort both the main links and filtered links
        def sort_key(x):
            if column == "favorite":
                return x.get("favorite", False)
            elif column == "name":
                return x.get("name", "").lower()
            elif column == "url":
                return x.get("url", "").lower()
            elif column == "date_added":
                return x.get("date_added", "")
            elif column == "last_opened":
                return x.get("last_opened") or ""
            return ""
        
        self.links.sort(key=sort_key, reverse=self.sort_reverse)
        self.filtered_links.sort(key=sort_key, reverse=self.sort_reverse)
        
        # Update column headers to show sort direction
        self._update_column_headers()
        
        # Refresh the display
        self._refresh_list()
    
    def _update_column_headers(self):
        """Update column headers to show sort direction"""
        # Reset all headers
        self.tree.heading("#0", text="Fav")
        self.tree.heading("name", text="Name")
        self.tree.heading("url", text="URL")
        self.tree.heading("date_added", text="Date Added")
        self.tree.heading("last_opened", text="Last Opened")
        
        # Add sort indicator to current sort column
        if self.sort_column:
            indicator = " ↓" if self.sort_reverse else " ↑"
            if self.sort_column == "favorite":
                self.tree.heading("#0", text="Fav" + indicator)
            elif self.sort_column == "name":
                self.tree.heading("name", text="Name" + indicator)
            elif self.sort_column == "url":
                self.tree.heading("url", text="URL" + indicator)
            elif self.sort_column == "date_added":
                self.tree.heading("date_added", text="Date Added" + indicator)
            elif self.sort_column == "last_opened":
                self.tree.heading("last_opened", text="Last Opened" + indicator)

    def _deselect_all(self, event):
        self.tree.selection_clear()


if __name__ == "__main__":
    root = tk.Tk()
    app = LinkApp(root)
    root.mainloop()
