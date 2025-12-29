"""
Dialog for displaying comprehensive link analytics and statistics.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional, Callable
from datetime import datetime
import threading

from models.link import Link
from models.profile import Profile


class AnalyticsDialog:
    """Dialog for showing comprehensive link analytics and statistics."""

    def __init__(self, parent: tk.Tk, profile: Profile, all_profiles: List[Profile],
                 analytics_service, browser_service, profile_service):
        self._parent = parent
        self._profile = profile
        self._all_profiles = all_profiles
        self._analytics_service = analytics_service
        self._browser_service = browser_service
        self._profile_service = profile_service
        self._dialog = None
        self._current_links = []  # Store current list for double-click handling
        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create and show the analytics dialog."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title(f"Analytics - {self._profile.name}")
        self._dialog.geometry("800x600")

        # Create notebook for tabs
        notebook = ttk.Notebook(self._dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Overview
        overview_tab = tk.Frame(notebook)
        notebook.add(overview_tab, text="Overview")
        self._create_overview_tab(overview_tab)

        # Tab 2: Trends
        trends_tab = tk.Frame(notebook)
        notebook.add(trends_tab, text="Trends")
        self._create_trends_tab(trends_tab)

        # Tab 3: Recommendations
        recommendations_tab = tk.Frame(notebook)
        notebook.add(recommendations_tab, text="Recommendations")
        self._create_recommendations_tab(recommendations_tab)

        # Tab 4: Categories & Tags
        categories_tab = tk.Frame(notebook)
        notebook.add(categories_tab, text="Categories & Tags")
        self._create_categories_tab(categories_tab)

        # Tab 5: Link Health
        health_tab = tk.Frame(notebook)
        notebook.add(health_tab, text="Link Health")
        self._create_health_tab(health_tab)

        # Tab 6: Most Opened
        most_opened_tab = tk.Frame(notebook)
        notebook.add(most_opened_tab, text="Most Opened")
        self._create_most_opened_tab(most_opened_tab)

        # Bottom button frame
        btn_frame = tk.Frame(self._dialog)
        btn_frame.pack(pady=(0, 10))

        tk.Button(btn_frame, text="Refresh", command=self._refresh_analytics, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", command=self._dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)

        # Configure dialog
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

    # ===== TAB 1: OVERVIEW =====

    def _create_overview_tab(self, parent: tk.Frame) -> None:
        """Create the overview statistics tab."""
        stats = self._analytics_service.get_profile_stats(self._profile)

        # Current profile stats
        stats_frame = tk.LabelFrame(parent, text="Current Profile Statistics", padx=10, pady=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        stats_display = [
            ("Total Links:", stats["total_links"]),
            ("Favorites:", f"{stats['favorites']} ({stats['favorites_pct']:.1f}%)"),
            ("Read Links:", f"{stats['read']} ({stats['read_pct']:.1f}%)"),
            ("Unread Links:", f"{stats['unread']} ({stats['unread_pct']:.1f}%)"),
            ("Total Opens:", stats["total_opens"]),
            ("Average Opens per Link:", f"{stats['avg_opens']:.1f}"),
            ("Most Active Domain:", stats["most_active_domain"]),
        ]

        for i, (label, value) in enumerate(stats_display):
            tk.Label(stats_frame, text=label, font=("", 10, "bold"), anchor="w").grid(
                row=i, column=0, sticky="w", pady=5, padx=(0, 10)
            )
            tk.Label(stats_frame, text=str(value), font=("", 10), anchor="w").grid(
                row=i, column=1, sticky="w", pady=5
            )

        # All profiles summary
        all_stats = self._analytics_service.get_all_profiles_stats(self._all_profiles)

        all_frame = tk.LabelFrame(parent, text="All Profiles Summary", padx=10, pady=10)
        all_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        all_stats_display = [
            ("Total Profiles:", all_stats["total_profiles"]),
            ("Total Links:", all_stats["total_links"]),
            ("Total Favorites:", f"{all_stats['favorites']} ({all_stats['favorites_pct']:.1f}%)"),
            ("Total Opens:", all_stats["total_opens"]),
            ("Average Opens per Link:", f"{all_stats['avg_opens']:.1f}"),
        ]

        for i, (label, value) in enumerate(all_stats_display):
            tk.Label(all_frame, text=label, font=("", 10, "bold"), anchor="w").grid(
                row=i, column=0, sticky="w", pady=5, padx=(0, 10)
            )
            tk.Label(all_frame, text=str(value), font=("", 10), anchor="w").grid(
                row=i, column=1, sticky="w", pady=5
            )

    # ===== TAB 2: TRENDS =====

    def _create_trends_tab(self, parent: tk.Frame) -> None:
        """Create the usage trends tab."""
        trends = self._analytics_service.get_usage_trends(self._profile, days=30)

        # Summary frame
        summary_frame = tk.LabelFrame(parent, text="Last 30 Days Summary", padx=10, pady=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(summary_frame, text=f"Total Opens: {trends['total_opens_in_period']}", font=("", 10)).pack(anchor="w", pady=2)
        tk.Label(summary_frame, text=f"Average per Day: {trends['avg_per_day']:.1f}", font=("", 10)).pack(anchor="w", pady=2)

        # Daily activity chart (text-based)
        chart_frame = tk.LabelFrame(parent, text="Daily Activity (Last 30 Days)", padx=10, pady=10)
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Create scrollable text widget for chart
        chart_text = tk.Text(chart_frame, height=15, width=70, font=("Courier", 9))
        chart_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(chart_frame, orient=tk.VERTICAL, command=chart_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        chart_text.config(yscrollcommand=scrollbar.set)

        # Generate text-based bar chart
        daily_counts = trends['daily_counts']
        max_count = max((count for _, count in daily_counts), default=1)

        for date, count in daily_counts:
            bars = '█' * int((count / max_count) * 40) if max_count > 0 else ''
            chart_text.insert(tk.END, f"{date}: {bars} {count}\n")

        chart_text.config(state=tk.DISABLED)

    # ===== TAB 3: RECOMMENDATIONS =====

    def _create_recommendations_tab(self, parent: tk.Frame) -> None:
        """Create the smart recommendations tab."""
        recommendations = self._analytics_service.get_recommended_links(self._profile, count=10)

        if not recommendations:
            tk.Label(parent, text="No recommendations available.", pady=20, font=("", 12)).pack()
            return

        # Info label
        info_label = tk.Label(parent, text="Links you might want to revisit:", font=("", 10))
        info_label.pack(anchor="w", padx=10, pady=10)

        # Create treeview for recommendations
        list_frame = tk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        columns = ("reason", "name", "url")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        tree.heading("reason", text="Reason")
        tree.column("reason", width=200, minwidth=150)

        tree.heading("name", text="Name")
        tree.column("name", width=250, minwidth=150)

        tree.heading("url", text="URL")
        tree.column("url", width=250, minwidth=150)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.config(yscrollcommand=scrollbar.set)

        # Populate with recommendations
        self._current_links = []
        for link, reason in recommendations:
            tree.insert("", "end", values=(reason, link.name, link.url))
            self._current_links.append(link)

        # Add double-click binding to open links
        tree.bind("<Double-1>", lambda e: self._on_recommendation_double_click(tree))

    def _on_recommendation_double_click(self, tree: ttk.Treeview) -> None:
        """Handle double-click on recommendation to open link."""
        selection = tree.selection()
        if selection:
            index = tree.index(selection[0])
            if index < len(self._current_links):
                link = self._current_links[index]
                self._browser_service.open_url(link.get_formatted_url())
                link.mark_as_opened()
                self._profile_service._save_current_profile()

    # ===== TAB 4: CATEGORIES & TAGS =====

    def _create_categories_tab(self, parent: tk.Frame) -> None:
        """Create the categories and tags breakdown tab."""
        # Category breakdown
        category_frame = tk.LabelFrame(parent, text="Categories", padx=10, pady=10)
        category_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        categories = self._analytics_service.get_category_breakdown(self._profile)
        self._create_breakdown_list(category_frame, categories)

        # Tag breakdown
        tag_frame = tk.LabelFrame(parent, text="Tags", padx=10, pady=10)
        tag_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        tags = self._analytics_service.get_tag_breakdown(self._profile)
        self._create_breakdown_list(tag_frame, tags)

        # Domain breakdown
        domain_frame = tk.LabelFrame(parent, text="Top Domains", padx=10, pady=10)
        domain_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        domains = self._analytics_service.get_most_active_domains(self._profile, limit=10)
        domain_list = tk.Text(domain_frame, height=10, width=60, font=("Courier", 10))
        domain_list.pack(fill=tk.BOTH, expand=True)

        for domain, count in domains:
            domain_list.insert(tk.END, f"{domain:30} {count} opens\n")

        domain_list.config(state=tk.DISABLED)

    def _create_breakdown_list(self, parent: tk.Frame, data: dict) -> None:
        """Create a text list showing breakdown data."""
        text_widget = tk.Text(parent, height=8, width=60, font=("Courier", 10))
        text_widget.pack(fill=tk.BOTH, expand=True)

        for item, count in data.items():
            # Create simple bar visualization
            max_width = 30
            total = sum(data.values())
            bar_width = int((count / total) * max_width) if total > 0 else 0
            bars = '█' * bar_width

            text_widget.insert(tk.END, f"{item:20} {bars} {count}\n")

        text_widget.config(state=tk.DISABLED)

    # ===== TAB 5: LINK HEALTH =====

    def _create_health_tab(self, parent: tk.Frame) -> None:
        """Create the link health monitoring tab."""
        # Health summary
        summary_frame = tk.LabelFrame(parent, text="Health Summary", padx=10, pady=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=10)

        broken_links = self._analytics_service.get_broken_links(self._profile)
        redirect_links = self._analytics_service.get_redirect_links(self._profile)
        unchecked_links = self._analytics_service.get_unchecked_links(self._profile)

        tk.Label(summary_frame, text=f"Broken Links: {len(broken_links)}", font=("", 10), fg="#F44336").pack(anchor="w", pady=2)
        tk.Label(summary_frame, text=f"Redirect Links: {len(redirect_links)}", font=("", 10), fg="#FFC107").pack(anchor="w", pady=2)
        tk.Label(summary_frame, text=f"Unchecked Links: {len(unchecked_links)}", font=("", 10), fg="#666666").pack(anchor="w", pady=2)

        # Check all links button
        btn_frame = tk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        check_btn = tk.Button(btn_frame, text="Check All Links Health", command=self._check_all_links_health)
        check_btn.pack(side=tk.LEFT, padx=5)

        self._health_progress_label = tk.Label(btn_frame, text="", font=("", 9))
        self._health_progress_label.pack(side=tk.LEFT, padx=10)

        # Problematic links list
        list_frame = tk.LabelFrame(parent, text="Problematic Links", padx=10, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        columns = ("status", "name", "url", "code")
        self._health_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        self._health_tree.heading("status", text="Status")
        self._health_tree.column("status", width=80, minwidth=80)

        self._health_tree.heading("name", text="Name")
        self._health_tree.column("name", width=200, minwidth=150)

        self._health_tree.heading("url", text="URL")
        self._health_tree.column("url", width=250, minwidth=150)

        self._health_tree.heading("code", text="HTTP Code")
        self._health_tree.column("code", width=80, minwidth=80)

        self._health_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._health_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._health_tree.config(yscrollcommand=scrollbar.set)

        # Populate with problematic links
        self._populate_health_tree(broken_links, redirect_links)

        # Add double-click binding
        self._health_tree.bind("<Double-1>", lambda e: self._on_health_tree_double_click())

    def _populate_health_tree(self, broken_links: List[Link], redirect_links: List[Link]) -> None:
        """Populate the health tree with problematic links."""
        self._current_links = []

        for link in broken_links:
            self._health_tree.insert("", "end", values=("Broken", link.name, link.url, link.http_status_code or "N/A"))
            self._current_links.append(link)

        for link in redirect_links:
            self._health_tree.insert("", "end", values=("Redirect", link.name, link.url, link.http_status_code or "N/A"))
            self._current_links.append(link)

    def _on_health_tree_double_click(self) -> None:
        """Handle double-click on health tree to open link."""
        selection = self._health_tree.selection()
        if selection:
            index = self._health_tree.index(selection[0])
            if index < len(self._current_links):
                link = self._current_links[index]
                self._browser_service.open_url(link.get_formatted_url())
                link.mark_as_opened()
                self._profile_service._save_current_profile()

    def _check_all_links_health(self) -> None:
        """Check health of all links in background."""
        links = self._profile.links

        def check_health_thread():
            def progress_callback(current, total):
                self._dialog.after(0, lambda: self._health_progress_label.config(
                    text=f"Checking {current}/{total}..."
                ))

            self._analytics_service.check_links_health_batch(links, callback=progress_callback)

            # Update UI when done
            self._dialog.after(0, self._on_health_check_complete)

        # Start background thread
        thread = threading.Thread(target=check_health_thread, daemon=True)
        thread.start()
        self._health_progress_label.config(text="Starting health check...")

    def _on_health_check_complete(self) -> None:
        """Handle completion of health check."""
        self._health_progress_label.config(text="Health check complete!")
        self._profile_service._save_current_profile()

        # Refresh the health tree
        self._health_tree.delete(*self._health_tree.get_children())
        broken_links = self._analytics_service.get_broken_links(self._profile)
        redirect_links = self._analytics_service.get_redirect_links(self._profile)
        self._populate_health_tree(broken_links, redirect_links)

        messagebox.showinfo("Health Check", "Link health check completed!")

    # ===== TAB 6: MOST OPENED =====

    def _create_most_opened_tab(self, parent: tk.Frame) -> None:
        """Create the most opened links tab."""
        most_opened = self._analytics_service.get_most_opened_links(self._profile, limit=20)

        if not most_opened:
            tk.Label(parent, text="No links with open count data.", pady=20, font=("", 12)).pack()
            return

        # Create treeview
        list_frame = tk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("rank", "opens", "name", "url", "last_opened", "category")
        self._most_opened_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)

        self._most_opened_tree.heading("rank", text="#")
        self._most_opened_tree.column("rank", width=40, minwidth=40)

        self._most_opened_tree.heading("opens", text="Opens")
        self._most_opened_tree.column("opens", width=60, minwidth=60)

        self._most_opened_tree.heading("name", text="Name")
        self._most_opened_tree.column("name", width=250, minwidth=150)

        self._most_opened_tree.heading("url", text="URL")
        self._most_opened_tree.column("url", width=200, minwidth=150)

        self._most_opened_tree.heading("last_opened", text="Last Opened")
        self._most_opened_tree.column("last_opened", width=120, minwidth=100)

        self._most_opened_tree.heading("category", text="Category")
        self._most_opened_tree.column("category", width=100, minwidth=80)

        self._most_opened_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._most_opened_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._most_opened_tree.config(yscrollcommand=scrollbar.set)

        # Populate with data
        self._current_links = most_opened
        for rank, link in enumerate(most_opened, 1):
            last_opened = self._format_date(link.last_opened) if link.last_opened else "Never"
            category = link.category or "Uncategorized"
            self._most_opened_tree.insert("", "end", values=(rank, link.open_count, link.name, link.url, last_opened, category))

        # Add double-click binding (CRITICAL FIX!)
        self._most_opened_tree.bind("<Double-1>", lambda e: self._on_most_opened_double_click())

    def _on_most_opened_double_click(self) -> None:
        """Handle double-click on most opened link to open it."""
        selection = self._most_opened_tree.selection()
        if selection:
            index = self._most_opened_tree.index(selection[0])
            if index < len(self._current_links):
                link = self._current_links[index]
                self._browser_service.open_url(link.get_formatted_url())
                link.mark_as_opened()
                self._profile_service._save_current_profile()

    # ===== HELPER METHODS =====

    def _format_date(self, date_str: Optional[str]) -> str:
        """Format ISO datetime string to readable format."""
        if not date_str:
            return "Never"
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            return "Unknown"

    def _refresh_analytics(self) -> None:
        """Refresh all analytics data."""
        self._dialog.destroy()
        # Recreate dialog with fresh data
        new_dialog = AnalyticsDialog(
            self._parent,
            self._profile,
            self._all_profiles,
            self._analytics_service,
            self._browser_service,
            self._profile_service
        )
        new_dialog.show()

    def show(self) -> None:
        """Show the dialog."""
        self._dialog.wait_window()
