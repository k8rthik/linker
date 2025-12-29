"""
Service for analytics calculations and insights.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import requests

from models.link import Link
from models.profile import Profile


class AnalyticsService:
    """Service for calculating analytics and generating insights."""

    def __init__(self, profile_service):
        """Initialize analytics service."""
        self._profile_service = profile_service

    # ===== CORE STATISTICS =====

    def get_profile_stats(self, profile: Profile) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a profile.

        Args:
            profile: The profile to analyze

        Returns:
            Dictionary with all statistics
        """
        links = profile.links
        total_links = len(links)

        if total_links == 0:
            return self._get_empty_stats()

        favorite_count = sum(1 for link in links if link.favorite)
        unread_count = sum(1 for link in links if link.is_unread())
        read_count = total_links - unread_count
        total_opens = sum(link.open_count for link in links)
        avg_opens = total_opens / total_links if total_links > 0 else 0

        # Domain breakdown
        domain_counts = self.get_domain_breakdown(profile)
        most_active_domain = max(domain_counts.items(), key=lambda x: x[1])[0] if domain_counts else "N/A"

        return {
            "total_links": total_links,
            "favorites": favorite_count,
            "favorites_pct": (favorite_count / total_links * 100) if total_links > 0 else 0,
            "read": read_count,
            "read_pct": (read_count / total_links * 100) if total_links > 0 else 0,
            "unread": unread_count,
            "unread_pct": (unread_count / total_links * 100) if total_links > 0 else 0,
            "total_opens": total_opens,
            "avg_opens": avg_opens,
            "most_active_domain": most_active_domain
        }

    def get_all_profiles_stats(self, profiles: List[Profile]) -> Dict[str, Any]:
        """
        Get aggregated statistics across all profiles.

        Args:
            profiles: List of all profiles

        Returns:
            Dictionary with aggregated statistics
        """
        total_links = 0
        total_favorites = 0
        total_unread = 0
        total_opens = 0

        for profile in profiles:
            links = profile.links
            total_links += len(links)
            total_favorites += sum(1 for link in links if link.favorite)
            total_unread += sum(1 for link in links if link.is_unread())
            total_opens += sum(link.open_count for link in links)

        read_count = total_links - total_unread
        avg_opens = total_opens / total_links if total_links > 0 else 0

        return {
            "total_profiles": len(profiles),
            "total_links": total_links,
            "favorites": total_favorites,
            "favorites_pct": (total_favorites / total_links * 100) if total_links > 0 else 0,
            "read": read_count,
            "read_pct": (read_count / total_links * 100) if total_links > 0 else 0,
            "unread": total_unread,
            "unread_pct": (total_unread / total_links * 100) if total_links > 0 else 0,
            "total_opens": total_opens,
            "avg_opens": avg_opens
        }

    def get_most_opened_links(self, profile: Profile, limit: int = 10) -> List[Link]:
        """
        Get the most opened links from a profile.

        Args:
            profile: The profile to analyze
            limit: Maximum number of links to return

        Returns:
            List of links sorted by open_count (highest first)
        """
        links = [link for link in profile.links if link.open_count > 0]
        sorted_links = sorted(links, key=lambda l: l.open_count, reverse=True)
        return sorted_links[:limit]

    # ===== TREND ANALYSIS =====

    def get_usage_trends(self, profile: Profile, days: int = 30) -> Dict[str, Any]:
        """
        Calculate usage trends over time.

        Args:
            profile: The profile to analyze
            days: Number of days to look back

        Returns:
            Dictionary with trend data
        """
        links = profile.links
        cutoff_date = datetime.now() - timedelta(days=days)

        # Count opens in the period
        recent_opens = 0
        for link in links:
            if link.last_opened:
                try:
                    last_opened_dt = datetime.fromisoformat(link.last_opened)
                    if last_opened_dt >= cutoff_date:
                        recent_opens += 1
                except (ValueError, AttributeError):
                    pass

        # Get daily counts
        daily_counts = self.get_daily_open_counts(links, days)

        return {
            "period_days": days,
            "total_opens_in_period": recent_opens,
            "daily_counts": daily_counts,
            "avg_per_day": recent_opens / days if days > 0 else 0
        }

    def get_daily_open_counts(self, links: List[Link], days: int) -> List[Tuple[str, int]]:
        """
        Get daily open counts for the specified period.

        Args:
            links: List of links to analyze
            days: Number of days to look back

        Returns:
            List of (date, count) tuples
        """
        daily_counts = defaultdict(int)
        cutoff_date = datetime.now() - timedelta(days=days)

        for link in links:
            if link.last_opened:
                try:
                    last_opened_dt = datetime.fromisoformat(link.last_opened)
                    if last_opened_dt >= cutoff_date:
                        date_str = last_opened_dt.strftime("%Y-%m-%d")
                        daily_counts[date_str] += 1
                except (ValueError, AttributeError):
                    pass

        # Create list of all dates in range
        result = []
        for i in range(days):
            date = datetime.now() - timedelta(days=days - i - 1)
            date_str = date.strftime("%Y-%m-%d")
            result.append((date_str, daily_counts.get(date_str, 0)))

        return result

    def get_weekly_aggregates(self, links: List[Link]) -> Dict[str, int]:
        """
        Get weekly aggregated open counts.

        Args:
            links: List of links to analyze

        Returns:
            Dictionary mapping week label to count
        """
        weekly_counts = defaultdict(int)

        for link in links:
            if link.last_opened:
                try:
                    last_opened_dt = datetime.fromisoformat(link.last_opened)
                    # Calculate week label (e.g., "Week 1", "Week 2")
                    weeks_ago = (datetime.now() - last_opened_dt).days // 7
                    if weeks_ago < 4:  # Only last 4 weeks
                        week_label = f"Week {4 - weeks_ago}"
                        weekly_counts[week_label] += 1
                except (ValueError, AttributeError):
                    pass

        return dict(weekly_counts)

    # ===== SMART RECOMMENDATIONS =====

    def get_recommended_links(self, profile: Profile, count: int = 5) -> List[Tuple[Link, str]]:
        """
        Get smart recommendations for links to revisit.

        Args:
            profile: The profile to analyze
            count: Maximum number of recommendations

        Returns:
            List of (link, reason) tuples
        """
        recommendations = []

        # Forgotten favorites (favorited but never opened)
        forgotten = self.get_forgotten_favorites(profile)
        for link in forgotten[:count]:
            recommendations.append((link, "Favorited but never opened"))

        # Stale links (opened long ago)
        if len(recommendations) < count:
            stale = self.get_stale_links(profile, days=90)
            for link in stale[:count - len(recommendations)]:
                recommendations.append((link, "Not opened in 90+ days"))

        # Unread old links (added but never opened)
        if len(recommendations) < count:
            unread_old = self._get_old_unread_links(profile, days=30)
            for link in unread_old[:count - len(recommendations)]:
                recommendations.append((link, "Added 30+ days ago, never opened"))

        return recommendations[:count]

    def get_stale_links(self, profile: Profile, days: int = 90) -> List[Link]:
        """
        Get links that haven't been opened in a while.

        Args:
            profile: The profile to analyze
            days: Number of days to consider stale

        Returns:
            List of stale links
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        stale_links = []

        for link in profile.links:
            if link.last_opened:
                try:
                    last_opened_dt = datetime.fromisoformat(link.last_opened)
                    if last_opened_dt < cutoff_date:
                        stale_links.append(link)
                except (ValueError, AttributeError):
                    pass

        return sorted(stale_links, key=lambda l: l.last_opened or "")

    def get_forgotten_favorites(self, profile: Profile) -> List[Link]:
        """
        Get links that are favorited but have never been opened.

        Args:
            profile: The profile to analyze

        Returns:
            List of forgotten favorite links
        """
        forgotten = [link for link in profile.links if link.favorite and link.is_unread()]
        return sorted(forgotten, key=lambda l: l.date_added, reverse=True)

    def _get_old_unread_links(self, profile: Profile, days: int = 30) -> List[Link]:
        """Get links added a while ago but never opened."""
        cutoff_date = datetime.now() - timedelta(days=days)
        old_unread = []

        for link in profile.links:
            if link.is_unread():
                try:
                    date_added_dt = datetime.fromisoformat(link.date_added)
                    if date_added_dt < cutoff_date:
                        old_unread.append(link)
                except (ValueError, AttributeError):
                    pass

        return sorted(old_unread, key=lambda l: l.date_added)

    # ===== CATEGORY/TAG ANALYSIS =====

    def get_category_breakdown(self, profile: Profile) -> Dict[str, int]:
        """
        Get breakdown of links by category.

        Args:
            profile: The profile to analyze

        Returns:
            Dictionary mapping category to count
        """
        category_counts = defaultdict(int)

        for link in profile.links:
            category = link.category or "Uncategorized"
            category_counts[category] += 1

        return dict(category_counts)

    def get_tag_breakdown(self, profile: Profile) -> Dict[str, int]:
        """
        Get breakdown of links by tag.

        Args:
            profile: The profile to analyze

        Returns:
            Dictionary mapping tag to count
        """
        tag_counts = defaultdict(int)

        for link in profile.links:
            for tag in link.tags:
                tag_counts[tag] += 1

        # If no tags, show "No tags"
        if not tag_counts:
            tag_counts["No tags"] = len(profile.links)

        return dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))

    def get_domain_breakdown(self, profile: Profile) -> Dict[str, int]:
        """
        Get breakdown of links by domain.

        Args:
            profile: The profile to analyze

        Returns:
            Dictionary mapping domain to count
        """
        domain_counts = defaultdict(int)

        for link in profile.links:
            domain = link.domain or "Unknown"
            domain_counts[domain] += 1

        return dict(sorted(domain_counts.items(), key=lambda x: x[1], reverse=True))

    def get_most_active_domains(self, profile: Profile, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get the most frequently visited domains.

        Args:
            profile: The profile to analyze
            limit: Maximum number of domains to return

        Returns:
            List of (domain, open_count) tuples
        """
        domain_opens = defaultdict(int)

        for link in profile.links:
            domain = link.domain or "Unknown"
            domain_opens[domain] += link.open_count

        sorted_domains = sorted(domain_opens.items(), key=lambda x: x[1], reverse=True)
        return sorted_domains[:limit]

    # ===== LINK HEALTH MONITORING =====

    def check_link_health(self, link: Link) -> Tuple[str, Optional[int]]:
        """
        Check the health of a single link.

        Args:
            link: The link to check

        Returns:
            Tuple of (status, http_code)
        """
        try:
            response = requests.head(link.get_formatted_url(), timeout=5, allow_redirects=True)
            status_code = response.status_code

            if status_code == 200:
                status = "active"
            elif 300 <= status_code < 400:
                status = "redirect"
            elif status_code == 404:
                status = "broken"
            elif status_code >= 400:
                status = "error"
            else:
                status = "unknown"

            return (status, status_code)

        except requests.Timeout:
            return ("timeout", None)
        except requests.RequestException:
            return ("error", None)
        except Exception:
            return ("unknown", None)

    def check_links_health_batch(self, links: List[Link], callback=None) -> Dict[int, Tuple[str, Optional[int]]]:
        """
        Check health of multiple links.

        Args:
            links: List of links to check
            callback: Optional callback(index, total) for progress updates

        Returns:
            Dictionary mapping link index to (status, http_code)
        """
        results = {}

        for i, link in enumerate(links):
            if callback:
                callback(i + 1, len(links))

            status, code = self.check_link_health(link)
            results[i] = (status, code)

            # Update link with health info
            link.set_health_status(status, code)

        return results

    def get_broken_links(self, profile: Profile) -> List[Link]:
        """Get all broken links in a profile."""
        return [link for link in profile.links if link.link_status == "broken"]

    def get_redirect_links(self, profile: Profile) -> List[Link]:
        """Get all redirect links in a profile."""
        return [link for link in profile.links if link.link_status == "redirect"]

    def get_unchecked_links(self, profile: Profile) -> List[Link]:
        """Get all unchecked links in a profile."""
        return [link for link in profile.links if link.link_status == "unknown"]

    # ===== HELPER METHODS =====

    def _get_empty_stats(self) -> Dict[str, Any]:
        """Return empty stats when no links exist."""
        return {
            "total_links": 0,
            "favorites": 0,
            "favorites_pct": 0,
            "read": 0,
            "read_pct": 0,
            "unread": 0,
            "unread_pct": 0,
            "total_opens": 0,
            "avg_opens": 0,
            "most_active_domain": "N/A"
        }
