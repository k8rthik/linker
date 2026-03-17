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
from ui.components.link_viewer import LinkViewerComponent


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
        self._dialog.title(f"Analytics Dashboard - {self._profile.name}")
        self._dialog.geometry("1000x700")

        # Create notebook for tabs
        notebook = ttk.Notebook(self._dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Dashboard (new!)
        dashboard_tab = tk.Frame(notebook)
        notebook.add(dashboard_tab, text="Dashboard")
        self._create_dashboard_tab(dashboard_tab)

        # Tab 2: Overview
        overview_tab = tk.Frame(notebook)
        notebook.add(overview_tab, text="Overview")
        self._create_overview_tab(overview_tab)

        # Tab 3: Time Patterns (enhanced!)
        time_patterns_tab = tk.Frame(notebook)
        notebook.add(time_patterns_tab, text="Time Patterns")
        self._create_time_patterns_tab(time_patterns_tab)

        # Tab 4: Top Links (merged Engagement + Most Opened)
        top_links_tab = tk.Frame(notebook)
        notebook.add(top_links_tab, text="Top Links")
        self._create_top_links_tab(top_links_tab)

        # Tab 6: Recommendations
        recommendations_tab = tk.Frame(notebook)
        notebook.add(recommendations_tab, text="Recommendations")
        self._create_recommendations_tab(recommendations_tab)

        # Tab 7: Profile Comparison (new!)
        comparison_tab = tk.Frame(notebook)
        notebook.add(comparison_tab, text="Profile Comparison")
        self._create_comparison_tab(comparison_tab)

        # Tab 8: Domain Statistics
        domain_tab = tk.Frame(notebook)
        notebook.add(domain_tab, text="Domain Statistics")
        self._create_domain_tab(domain_tab)

        # Tab 9: Link Health
        health_tab = tk.Frame(notebook)
        notebook.add(health_tab, text="Link Health")
        self._create_health_tab(health_tab)

        # Bottom button frame
        btn_frame = tk.Frame(self._dialog)
        btn_frame.pack(pady=(0, 10))

        tk.Button(btn_frame, text="Export Report", command=self._export_report, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Refresh", command=self._refresh_analytics, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", command=self._dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

        # Configure dialog
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

    # ===== TAB 1: DASHBOARD (NEW!) =====

    def _create_dashboard_tab(self, parent: tk.Frame) -> None:
        """Create the main dashboard with key metrics and insights."""
        # Create scrollable canvas
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        # Get all the data we need
        stats = self._analytics_service.get_profile_stats(self._profile)
        streaks = self._analytics_service.get_usage_streaks(self._profile)
        health_score = self._analytics_service.get_profile_health_score(self._profile)
        peak_time, peak_count = self._analytics_service.get_peak_usage_time(self._profile)
        insights = self._analytics_service.get_productivity_insights(self._profile)

        # Title
        title = tk.Label(scrollable_frame, text="Your Link Analytics Dashboard",
                        font=("", 16, "bold"), fg="#2196F3")
        title.pack(pady=(10, 20))

        # Key Metrics Grid
        metrics_frame = tk.Frame(scrollable_frame)
        metrics_frame.pack(fill=tk.X, padx=20, pady=10)

        self._create_metric_card(metrics_frame, "Total Links", str(stats["total_links"]),
                                "#4CAF50", row=0, col=0)
        self._create_metric_card(metrics_frame, "Favorites",
                                f"{stats['favorites']} ({stats['favorites_pct']:.0f}%)",
                                "#FF9800", row=0, col=1)
        self._create_metric_card(metrics_frame, "Total Opens", str(stats["total_opens"]),
                                "#2196F3", row=0, col=2)
        self._create_metric_card(metrics_frame, "Avg Opens/Link", f"{stats['avg_opens']:.1f}",
                                "#9C27B0", row=0, col=3)

        self._create_metric_card(metrics_frame, "Current Streak",
                                f"{streaks['current_streak']} days",
                                "#F44336", row=1, col=0)
        self._create_metric_card(metrics_frame, "Longest Streak",
                                f"{streaks['longest_streak']} days",
                                "#FF5722", row=1, col=1)
        self._create_metric_card(metrics_frame, "Quality Score",
                                f"{health_score['overall_score']:.0f}/100",
                                "#00BCD4", row=1, col=2)
        self._create_metric_card(metrics_frame, "Unread Links",
                                f"{stats['unread']} ({stats['unread_pct']:.0f}%)",
                                "#FFC107", row=1, col=3)

        # Insights Section
        insights_frame = tk.LabelFrame(scrollable_frame, text="Insights & Recommendations",
                                      padx=15, pady=15, font=("", 11, "bold"))
        insights_frame.pack(fill=tk.X, padx=20, pady=15)

        for insight in insights:
            insight_label = tk.Label(insights_frame, text=insight, font=("", 10),
                                   anchor="w", wraplength=900, justify=tk.LEFT)
            insight_label.pack(fill=tk.X, pady=3)

        # Peak Usage Time
        if peak_count > 0:
            peak_frame = tk.LabelFrame(scrollable_frame, text="Usage Patterns",
                                      padx=15, pady=15, font=("", 11, "bold"))
            peak_frame.pack(fill=tk.X, padx=20, pady=15)

            tk.Label(peak_frame, text=f"Peak Activity Time: {peak_time}",
                    font=("", 10)).pack(anchor="w", pady=3)
            tk.Label(peak_frame, text=f"Total Active Days: {streaks['total_active_days']}",
                    font=("", 10)).pack(anchor="w", pady=3)
            tk.Label(peak_frame, text=f"Most Active Domain: {stats['most_active_domain']}",
                    font=("", 10)).pack(anchor="w", pady=3)

        # Quality Breakdown
        quality_frame = tk.LabelFrame(scrollable_frame, text="Link Quality Distribution",
                                     padx=15, pady=15, font=("", 11, "bold"))
        quality_frame.pack(fill=tk.X, padx=20, pady=15)

        quality_breakdown = health_score["quality_breakdown"]
        total = health_score["total_links"]

        for tier, count in quality_breakdown.items():
            if total > 0:
                pct = (count / total) * 100
                bar_width = int((count / total) * 50)
                bars = '█' * bar_width

                tier_label = tk.Label(quality_frame,
                                    text=f"{tier:20} {bars} {count} ({pct:.1f}%)",
                                    font=("Courier", 10), anchor="w")
                tier_label.pack(fill=tk.X, pady=2)

    def _create_metric_card(self, parent, title, value, color, row, col):
        """Create a metric card widget."""
        card = tk.Frame(parent, relief=tk.RAISED, borderwidth=2, bg=color)
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        parent.grid_columnconfigure(col, weight=1)

        tk.Label(card, text=title, font=("", 9), bg=color, fg="white").pack(pady=(8, 2))
        tk.Label(card, text=value, font=("", 14, "bold"), bg=color, fg="white").pack(pady=(2, 8))

    # ===== TAB 2: OVERVIEW =====

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

    # ===== TAB 3: TIME PATTERNS (ENHANCED!) =====

    def _create_time_patterns_tab(self, parent: tk.Frame) -> None:
        """Create the time-based usage patterns tab."""
        # Hourly distribution
        hourly_frame = tk.LabelFrame(parent, text="Activity by Hour of Day", padx=10, pady=10)
        hourly_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        hourly_data = self._analytics_service.get_hourly_distribution(self._profile)
        max_count = max(hourly_data.values()) if hourly_data else 1

        hourly_text = tk.Text(hourly_frame, height=12, width=70, font=("Courier", 9))
        hourly_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        hourly_scroll = ttk.Scrollbar(hourly_frame, orient=tk.VERTICAL, command=hourly_text.yview)
        hourly_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        hourly_text.config(yscrollcommand=hourly_scroll.set)

        for hour in range(24):
            count = hourly_data.get(hour, 0)
            bar_width = int((count / max_count) * 40) if max_count > 0 else 0
            bars = '█' * bar_width

            # Format hour nicely
            if hour == 0:
                time_label = "12 AM"
            elif hour < 12:
                time_label = f"{hour:2d} AM"
            elif hour == 12:
                time_label = "12 PM"
            else:
                time_label = f"{hour-12:2d} PM"

            hourly_text.insert(tk.END, f"{time_label:7} {bars} {count}\n")

        hourly_text.config(state=tk.DISABLED)

        # Day of week distribution
        dow_frame = tk.LabelFrame(parent, text="Activity by Day of Week", padx=10, pady=10)
        dow_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        dow_data = self._analytics_service.get_day_of_week_distribution(self._profile)
        max_dow = max(dow_data.values()) if dow_data else 1

        dow_text = tk.Text(dow_frame, height=8, width=70, font=("Courier", 10))
        dow_text.pack(fill=tk.BOTH, expand=True)

        for day, count in dow_data.items():
            bar_width = int((count / max_dow) * 40) if max_dow > 0 else 0
            bars = '█' * bar_width
            dow_text.insert(tk.END, f"{day:10} {bars} {count}\n")

        dow_text.config(state=tk.DISABLED)

    # ===== TAB 4: TOP LINKS (MERGED ENGAGEMENT + MOST OPENED) =====

    def _create_top_links_tab(self, parent: tk.Frame) -> None:
        """Create the top links tab with sorting options."""
        # Controls frame
        controls_frame = tk.Frame(parent)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(controls_frame, text="Sort by:", font=("", 10)).pack(side=tk.LEFT, padx=(0, 5))

        self._sort_by_var = tk.StringVar(value="engagement")
        sort_options = [
            ("Engagement Score", "engagement"),
            ("Open Count", "opens"),
            ("Last Opened", "last_opened"),
            ("Created Date", "created")
        ]

        for label, value in sort_options:
            tk.Radiobutton(
                controls_frame,
                text=label,
                variable=self._sort_by_var,
                value=value,
                command=self._update_top_links
            ).pack(side=tk.LEFT, padx=5)

        # Link viewer
        self._top_links_viewer = LinkViewerComponent(
            parent,
            show_columns=['rank', 'opens', 'score', 'name', 'favorite', 'last_opened']
        )
        self._top_links_viewer.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Set callbacks
        self._top_links_viewer.set_open_callback(self._open_link_and_save)
        # Note: Edit callback not set - read-only in analytics

        # Initial load
        self._update_top_links()

    def _update_top_links(self) -> None:
        """Update the top links display based on sort selection."""
        sort_by = self._sort_by_var.get()

        if sort_by == "engagement":
            # Sort by engagement score
            scored_links = []
            for link in self._profile.links:
                score = self._analytics_service.calculate_engagement_score(link)
                scored_links.append((link, score))
            scored_links.sort(key=lambda x: x[1], reverse=True)
            links = [link for link, _ in scored_links[:50]]

            # Custom data getter that includes engagement score
            def data_getter(link):
                score = self._analytics_service.calculate_engagement_score(link)
                rank = links.index(link) + 1
                return (
                    rank,
                    link.open_count,
                    f"{score:.0f}",
                    link.name,
                    "⭐" if link.favorite else "",
                    self._format_date(link.last_opened) if link.last_opened else "Never"
                )

        elif sort_by == "opens":
            # Sort by open count
            links = self._analytics_service.get_most_opened_links(self._profile, limit=50)

            def data_getter(link):
                rank = links.index(link) + 1
                return (
                    rank,
                    link.open_count,
                    "-",  # No score for this view
                    link.name,
                    "⭐" if link.favorite else "",
                    self._format_date(link.last_opened) if link.last_opened else "Never"
                )

        elif sort_by == "last_opened":
            # Sort by last opened
            links = [link for link in self._profile.links if link.last_opened]
            links.sort(key=lambda x: x.last_opened or "", reverse=True)
            links = links[:50]

            def data_getter(link):
                rank = links.index(link) + 1
                return (
                    rank,
                    link.open_count,
                    "-",
                    link.name,
                    "⭐" if link.favorite else "",
                    self._format_date(link.last_opened) if link.last_opened else "Never"
                )

        else:  # created
            # Sort by created date
            links = sorted(self._profile.links, key=lambda x: x.date_added or "", reverse=True)[:50]

            def data_getter(link):
                rank = links.index(link) + 1
                return (
                    rank,
                    link.open_count,
                    "-",
                    link.name,
                    "⭐" if link.favorite else "",
                    self._format_date(link.last_opened) if link.last_opened else "Never"
                )

        self._top_links_viewer.set_links(links, data_getter)

    def _open_link_and_save(self, link: Link) -> None:
        """Open a link and save the updated profile."""
        self._browser_service.open_url(link.get_formatted_url())
        link.mark_as_opened()
        self._profile_service._save_current_profile()

    # Note: The old _create_engagement_tab and _create_most_opened_tab methods have been
    # replaced by the new unified _create_top_links_tab method which uses LinkViewerComponent
    # for consistent formatting and includes context menu support

    # ===== TAB 6: RECOMMENDATIONS =====

    def _create_recommendations_tab(self, parent: tk.Frame) -> None:
        """Create the smart recommendations tab."""
        recommendations = self._analytics_service.get_recommended_links(self._profile, count=15)

        if not recommendations:
            tk.Label(parent, text="No recommendations available.", pady=20, font=("", 12)).pack()
            return

        info_label = tk.Label(parent, text="Links you might want to revisit:", font=("", 10))
        info_label.pack(anchor="w", padx=10, pady=10)

        # Use LinkViewerComponent
        self._recommendations_viewer = LinkViewerComponent(
            parent,
            show_columns=['reason', 'name', 'url', 'opens', 'favorite']
        )
        self._recommendations_viewer.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Set callbacks
        self._recommendations_viewer.set_open_callback(self._open_link_and_save)

        # Prepare links and data getter
        links = [link for link, _ in recommendations]
        reasons = {link: reason for link, reason in recommendations}

        def data_getter(link):
            return (
                reasons.get(link, ""),
                link.name,
                link.url,
                link.open_count,
                "⭐" if link.favorite else ""
            )

        self._recommendations_viewer.set_links(links, data_getter)

    # ===== TAB 7: PROFILE COMPARISON (NEW!) =====

    def _create_comparison_tab(self, parent: tk.Frame) -> None:
        """Create the profile comparison tab."""
        comparisons = self._analytics_service.compare_profiles(self._all_profiles)

        if len(comparisons) <= 1:
            tk.Label(parent, text="Create more profiles to see comparisons.",
                    pady=20, font=("", 12)).pack()
            return

        list_frame = tk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("rank", "profile", "links", "favorites", "opens", "avg_opens",
                  "quality", "streak", "active_days")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)

        tree.heading("rank", text="#")
        tree.column("rank", width=40, minwidth=40)

        tree.heading("profile", text="Profile")
        tree.column("profile", width=150, minwidth=100)

        tree.heading("links", text="Links")
        tree.column("links", width=60, minwidth=60)

        tree.heading("favorites", text="Favorites")
        tree.column("favorites", width=80, minwidth=70)

        tree.heading("opens", text="Total Opens")
        tree.column("opens", width=80, minwidth=70)

        tree.heading("avg_opens", text="Avg Opens")
        tree.column("avg_opens", width=80, minwidth=70)

        tree.heading("quality", text="Quality")
        tree.column("quality", width=70, minwidth=60)

        tree.heading("streak", text="Streak")
        tree.column("streak", width=60, minwidth=50)

        tree.heading("active_days", text="Active Days")
        tree.column("active_days", width=90, minwidth=80)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.config(yscrollcommand=scrollbar.set)

        for rank, comp in enumerate(comparisons, 1):
            tree.insert("", "end", values=(
                rank,
                comp["name"],
                comp["total_links"],
                comp["favorites"],
                comp["total_opens"],
                f"{comp['avg_opens']:.1f}",
                f"{comp['quality_score']:.0f}",
                comp["current_streak"],
                comp["active_days"]
            ))

    # ===== TAB 8: DOMAIN STATISTICS =====

    def _create_domain_tab(self, parent: tk.Frame) -> None:
        """Create the domain statistics tab."""
        # Top domains by link count
        link_count_frame = tk.LabelFrame(parent, text="Top Domains by Link Count", padx=10, pady=10)
        link_count_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        domain_breakdown = self._analytics_service.get_domain_breakdown(self._profile)
        if domain_breakdown:
            link_count_text = tk.Text(link_count_frame, height=12, width=70, font=("Courier", 10))
            link_count_text.pack(fill=tk.BOTH, expand=True)

            # Sort by count descending
            sorted_domains = sorted(domain_breakdown.items(), key=lambda x: x[1], reverse=True)[:20]
            for domain, count in sorted_domains:
                link_count_text.insert(tk.END, f"{domain:40} {count:4d} links\n")

            link_count_text.config(state=tk.DISABLED)
        else:
            tk.Label(link_count_frame, text="No domain data available.").pack()

        # Top domains by opens
        opens_frame = tk.LabelFrame(parent, text="Top Domains by Opens", padx=10, pady=10)
        opens_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        domains = self._analytics_service.get_most_active_domains(self._profile, limit=20)
        if domains:
            domain_list = tk.Text(opens_frame, height=12, width=70, font=("Courier", 10))
            domain_list.pack(fill=tk.BOTH, expand=True)

            for domain, count in domains:
                domain_list.insert(tk.END, f"{domain:40} {count:4d} opens\n")

            domain_list.config(state=tk.DISABLED)
        else:
            tk.Label(opens_frame, text="No domain activity data available.").pack()

    # ===== TAB 9: LINK HEALTH =====

    def _create_health_tab(self, parent: tk.Frame) -> None:
        """Create the link health monitoring tab."""
        summary_frame = tk.LabelFrame(parent, text="Health Summary", padx=10, pady=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=10)

        broken_links = self._analytics_service.get_broken_links(self._profile)
        redirect_links = self._analytics_service.get_redirect_links(self._profile)
        unchecked_links = self._analytics_service.get_unchecked_links(self._profile)

        tk.Label(summary_frame, text=f"Broken Links: {len(broken_links)}",
                font=("", 10), fg="#F44336").pack(anchor="w", pady=2)
        tk.Label(summary_frame, text=f"Redirect Links: {len(redirect_links)}",
                font=("", 10), fg="#FFC107").pack(anchor="w", pady=2)
        tk.Label(summary_frame, text=f"Unchecked Links: {len(unchecked_links)}",
                font=("", 10), fg="#666666").pack(anchor="w", pady=2)

        btn_frame = tk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        check_btn = tk.Button(btn_frame, text="Check All Links Health",
                             command=self._check_all_links_health)
        check_btn.pack(side=tk.LEFT, padx=5)

        self._health_progress_label = tk.Label(btn_frame, text="", font=("", 9))
        self._health_progress_label.pack(side=tk.LEFT, padx=10)

        # Create container for link viewer
        viewer_container = tk.Frame(parent)
        viewer_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Add label
        tk.Label(viewer_container, text="Problematic Links", font=("", 10, "bold")).pack(anchor="w", pady=(0, 5))

        # Use LinkViewerComponent
        self._health_viewer = LinkViewerComponent(
            viewer_container,
            show_columns=['health_status', 'name', 'url', 'http_code', 'opens']
        )
        self._health_viewer.pack(fill=tk.BOTH, expand=True)

        # Set callbacks
        self._health_viewer.set_open_callback(self._open_link_and_save)

        # Initial populate
        self._populate_health_viewer(broken_links, redirect_links)

    def _populate_health_viewer(self, broken_links: List[Link], redirect_links: List[Link]) -> None:
        """Populate the health viewer with problematic links."""
        # Combine broken and redirect links
        all_problematic = []
        statuses = {}

        for link in broken_links:
            all_problematic.append(link)
            statuses[link] = "Broken"

        for link in redirect_links:
            all_problematic.append(link)
            statuses[link] = "Redirect"

        # Data getter for health viewer
        def data_getter(link):
            return (
                statuses.get(link, "Unknown"),
                link.name,
                link.url,
                link.http_status_code or "N/A",
                link.open_count
            )

        self._health_viewer.set_links(all_problematic, data_getter)

    def _check_all_links_health(self) -> None:
        """Check health of all links in background."""
        links = self._profile.links

        def check_health_thread():
            def progress_callback(current, total):
                self._dialog.after(0, lambda: self._health_progress_label.config(
                    text=f"Checking {current}/{total}..."
                ))

            self._analytics_service.check_links_health_batch(links, callback=progress_callback)
            self._dialog.after(0, self._on_health_check_complete)

        thread = threading.Thread(target=check_health_thread, daemon=True)
        thread.start()
        self._health_progress_label.config(text="Starting health check...")

    def _on_health_check_complete(self) -> None:
        """Handle completion of health check."""
        self._health_progress_label.config(text="Health check complete!")
        self._profile_service._save_current_profile()

        # Refresh the health viewer with updated data
        broken_links = self._analytics_service.get_broken_links(self._profile)
        redirect_links = self._analytics_service.get_redirect_links(self._profile)
        self._populate_health_viewer(broken_links, redirect_links)

        messagebox.showinfo("Health Check", "Link health check completed!")

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

    def _export_report(self) -> None:
        """Export analytics report to JSON file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"analytics_{self._profile.name}_{datetime.now().strftime('%Y%m%d')}.json"
        )

        if file_path:
            try:
                report = self._analytics_service.export_analytics_report(
                    self._profile, self._all_profiles
                )
                with open(file_path, 'w') as f:
                    f.write(report)
                messagebox.showinfo("Export Complete", f"Analytics report exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export report:\n{str(e)}")

    def _refresh_analytics(self) -> None:
        """Refresh all analytics data."""
        self._dialog.destroy()
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
