import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import List, Callable, Dict
from models.link import Link


class TagManagerDialog:
    """Dialog for managing tags (view, rename, merge, delete)."""

    def __init__(self, parent: tk.Tk, get_all_links: Callable[[], List[Link]],
                 update_link: Callable[[int, Link], bool],
                 on_filter_by_tag: Callable[[str], None]):
        self._parent = parent
        self._get_all_links = get_all_links
        self._update_link = update_link
        self._on_filter_by_tag = on_filter_by_tag
        self._dialog: tk.Toplevel = None
        self._tag_stats: Dict[str, int] = {}
        self._tree: ttk.Treeview = None
        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create and show the tag manager dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Tag Manager")
        self._dialog.geometry("600x500")
        self._dialog.resizable(True, True)

        # Main frame
        main_frame = tk.Frame(self._dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        tk.Label(main_frame, text="Tag Manager", font=("TkDefaultFont", 14, "bold")).pack(
            pady=(0, 10))

        # Instructions
        tk.Label(main_frame, text="View and manage all tags in your current profile",
                fg="gray").pack(pady=(0, 15))

        # Tag list with treeview
        list_frame = tk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview
        self._tree = ttk.Treeview(list_frame, columns=("tag", "count"), show="headings",
                                   yscrollcommand=scrollbar.set)
        self._tree.heading("tag", text="Tag Name")
        self._tree.heading("count", text="Usage Count")
        self._tree.column("tag", width=400)
        self._tree.column("count", width=100, anchor=tk.CENTER)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self._tree.yview)

        # Button frame
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Button(btn_frame, text="Filter by Tag", command=self._filter_by_selected_tag,
                 width=15).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="Rename Tag", command=self._rename_selected_tag,
                 width=15).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="Merge Tags", command=self._merge_tags,
                 width=15).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="Delete Tag", command=self._delete_selected_tag,
                 width=15).pack(side=tk.LEFT)

        # Close button
        tk.Button(main_frame, text="Close", command=self._dialog.destroy,
                 width=12).pack()

        # Load and display tags
        self._refresh_tags()

        # Center dialog
        self._dialog.update_idletasks()
        x = (self._dialog.winfo_screenwidth() // 2) - (self._dialog.winfo_width() // 2)
        y = (self._dialog.winfo_screenheight() // 2) - (self._dialog.winfo_height() // 2)
        self._dialog.geometry(f"+{x}+{y}")

        # Make modal
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

    def _refresh_tags(self) -> None:
        """Refresh the tag list with current data."""
        # Clear existing items
        for item in self._tree.get_children():
            self._tree.delete(item)

        # Calculate tag statistics
        self._tag_stats = {}
        links = self._get_all_links()

        for link in links:
            for tag in link.tags:
                self._tag_stats[tag] = self._tag_stats.get(tag, 0) + 1

        # Sort tags alphabetically
        sorted_tags = sorted(self._tag_stats.items())

        # Add to treeview
        for tag, count in sorted_tags:
            self._tree.insert("", tk.END, values=(tag, count))

    def _get_selected_tag(self) -> str:
        """Get the currently selected tag."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a tag first.")
            return None

        item = self._tree.item(selection[0])
        return item["values"][0]

    def _filter_by_selected_tag(self) -> None:
        """Filter links by the selected tag."""
        tag = self._get_selected_tag()
        if tag:
            self._on_filter_by_tag(tag)
            self._dialog.destroy()

    def _rename_selected_tag(self) -> None:
        """Rename the selected tag across all links."""
        old_tag = self._get_selected_tag()
        if not old_tag:
            return

        new_tag = simpledialog.askstring(
            "Rename Tag",
            f"Rename '{old_tag}' to:",
            initialvalue=old_tag,
            parent=self._dialog
        )

        if not new_tag or new_tag == old_tag:
            return

        new_tag = new_tag.strip()
        if not new_tag:
            messagebox.showerror("Error", "Tag name cannot be empty.")
            return

        # Rename tag in all links
        links = self._get_all_links()
        updated_count = 0

        for idx, link in enumerate(links):
            if old_tag in link.tags:
                link.remove_tag(old_tag)
                link.add_tag(new_tag)
                self._update_link(idx, link)
                updated_count += 1

        messagebox.showinfo("Success", f"Renamed tag '{old_tag}' to '{new_tag}' in {updated_count} link(s).")
        self._refresh_tags()

    def _merge_tags(self) -> None:
        """Merge multiple tags into one."""
        tags_input = simpledialog.askstring(
            "Merge Tags",
            "Enter tags to merge (comma-separated):\n\nExample: python, Python, PYTHON",
            parent=self._dialog
        )

        if not tags_input:
            return

        tags_to_merge = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
        if len(tags_to_merge) < 2:
            messagebox.showerror("Error", "Please enter at least 2 tags to merge.")
            return

        target_tag = simpledialog.askstring(
            "Merge Tags",
            f"Merge these tags:\n{', '.join(tags_to_merge)}\n\nInto:",
            initialvalue=tags_to_merge[0],
            parent=self._dialog
        )

        if not target_tag:
            return

        target_tag = target_tag.strip()
        if not target_tag:
            messagebox.showerror("Error", "Target tag name cannot be empty.")
            return

        # Merge tags in all links
        links = self._get_all_links()
        updated_count = 0

        for idx, link in enumerate(links):
            has_any_merge_tag = any(tag in link.tags for tag in tags_to_merge)
            if has_any_merge_tag:
                # Remove all merge tags
                for tag in tags_to_merge:
                    if tag in link.tags:
                        link.remove_tag(tag)
                # Add target tag
                link.add_tag(target_tag)
                self._update_link(idx, link)
                updated_count += 1

        messagebox.showinfo("Success", f"Merged {len(tags_to_merge)} tags into '{target_tag}' across {updated_count} link(s).")
        self._refresh_tags()

    def _delete_selected_tag(self) -> None:
        """Delete the selected tag from all links."""
        tag = self._get_selected_tag()
        if not tag:
            return

        count = self._tag_stats.get(tag, 0)
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete tag '{tag}' from {count} link(s)?\n\nThis cannot be undone.",
            parent=self._dialog
        )

        if not confirm:
            return

        # Remove tag from all links
        links = self._get_all_links()
        updated_count = 0

        for idx, link in enumerate(links):
            if tag in link.tags:
                link.remove_tag(tag)
                self._update_link(idx, link)
                updated_count += 1

        messagebox.showinfo("Success", f"Deleted tag '{tag}' from {updated_count} link(s).")
        self._refresh_tags()
