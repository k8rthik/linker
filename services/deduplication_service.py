"""
Service for detecting and merging duplicate links within a profile.
"""

from typing import List, Dict, Tuple, Optional
from models.link import Link
from models.profile import Profile


class DeduplicationService:
    """Service for deduplicating links with intelligent merging."""

    def __init__(self):
        pass

    def find_duplicates(self, profile: Profile) -> Dict[str, List[Link]]:
        """
        Find all duplicate link groups in a profile.

        Args:
            profile: The profile to analyze

        Returns:
            Dictionary mapping normalized URL to list of duplicate links
        """
        url_groups = {}

        for link in profile.links:
            normalized_url = self._normalize_url(link.url)
            if normalized_url not in url_groups:
                url_groups[normalized_url] = []
            url_groups[normalized_url].append(link)

        # Filter to only groups with duplicates (2+ links)
        duplicates = {url: links for url, links in url_groups.items() if len(links) > 1}
        return duplicates

    def deduplicate_profile(self, profile: Profile) -> Tuple[int, int, List[Tuple[Link, Link]]]:
        """
        Deduplicate links in a profile with automatic merging.

        Args:
            profile: The profile to deduplicate

        Returns:
            Tuple of (auto_merged_count, removed_count, conflicts_requiring_manual_resolution)
        """
        duplicate_groups = self.find_duplicates(profile)

        if not duplicate_groups:
            return (0, 0, [])

        auto_merged = 0
        removed = 0
        conflicts = []

        # Work with all_links to get correct indices
        all_links = profile.all_links

        for normalized_url, duplicates in duplicate_groups.items():
            # Try to auto-merge this group
            result = self._merge_duplicate_group(duplicates)

            if result["type"] == "auto_merged":
                # Replace all duplicates with the merged link
                merged_link = result["merged_link"]
                links_to_remove = result["removed_links"]

                # Find indices and remove duplicates (in reverse order to maintain indices)
                indices_to_remove = []
                for link_to_remove in links_to_remove:
                    try:
                        # Find index in all_links
                        idx = all_links.index(link_to_remove)
                        indices_to_remove.append(idx)
                    except ValueError:
                        pass  # Link not found

                # Remove in reverse order to maintain correct indices
                for idx in sorted(indices_to_remove, reverse=True):
                    # Convert all_links index to non-archived index
                    non_archived = [l for l in all_links if not l.is_archived()]
                    if all_links[idx] in non_archived:
                        non_archived_idx = non_archived.index(all_links[idx])
                        if profile.remove_link(non_archived_idx):
                            removed += 1

                # Add merged link
                profile.add_link(merged_link)

                auto_merged += 1

            elif result["type"] == "conflict":
                # Add to conflicts for manual resolution
                conflicts.extend(result["conflicts"])

        return (auto_merged, removed, conflicts)

    def _merge_duplicate_group(self, duplicates: List[Link]) -> Dict:
        """
        Attempt to merge a group of duplicate links.

        Returns:
            Dictionary with "type" key:
            - "auto_merged": Successfully merged, includes "merged_link" and "removed_links"
            - "conflict": Manual resolution needed, includes "conflicts" list of tuples
        """
        # Check for conflicts (multiple custom names)
        custom_named_links = [link for link in duplicates if not self._is_url_name(link.name, link.url)]

        if len(custom_named_links) > 1:
            # Conflict: multiple custom names
            # Generate all pairwise conflicts for user resolution
            conflicts = []
            for i in range(len(custom_named_links)):
                for j in range(i + 1, len(custom_named_links)):
                    conflicts.append((custom_named_links[i], custom_named_links[j]))
            return {"type": "conflict", "conflicts": conflicts}

        # No conflict, proceed with auto-merge
        merged_link = self._merge_links_auto(duplicates)
        removed_links = [link for link in duplicates if link != merged_link]

        return {
            "type": "auto_merged",
            "merged_link": merged_link,
            "removed_links": duplicates  # Remove all, will re-add merged
        }

    def _merge_links_auto(self, links: List[Link]) -> Link:
        """
        Automatically merge multiple links with the same URL.

        Priority rules:
        - Name: Custom name > URL name (prefer longer custom names)
        - Favorite: True if any link is favorite
        - Date added: Oldest date
        - Last opened: Latest date
        - Open count: Sum of all counts
        - Other fields: Intelligent merging
        """
        # Choose the best name
        custom_named_links = [link for link in links if not self._is_url_name(link.name, link.url)]
        if custom_named_links:
            # Pick the longest custom name
            merged_name = max(custom_named_links, key=lambda l: len(l.name)).name
        else:
            # All are URL names, pick the first one
            merged_name = links[0].name

        # Merge favorite status (true if any is favorite)
        merged_favorite = any(link.favorite for link in links)

        # Keep oldest date_added
        date_added_values = [link.date_added for link in links if link.date_added]
        merged_date_added = min(date_added_values) if date_added_values else links[0].date_added

        # Keep most recent last_opened
        last_opened_values = [link.last_opened for link in links if link.last_opened]
        merged_last_opened = max(last_opened_values) if last_opened_values else None

        # Sum open_count
        merged_open_count = sum(link.open_count for link in links)

        # Merge archived status (true if any is archived)
        merged_archived = any(link.archived for link in links)

        # Keep earliest first_opened
        first_opened_values = [link.first_opened for link in links if link.first_opened]
        merged_first_opened = min(first_opened_values) if first_opened_values else None

        # Sum favorite_toggle_count
        merged_toggle_count = sum(link.favorite_toggle_count for link in links)

        # Keep most recent last_modified
        last_modified_values = [link.last_modified for link in links if link.last_modified]
        merged_last_modified = max(last_modified_values) if last_modified_values else None

        # Use time_to_first_open from the link with earliest first_opened
        merged_time_to_first_open = None
        if merged_first_opened:
            for link in links:
                if link.first_opened == merged_first_opened:
                    merged_time_to_first_open = link.time_to_first_open
                    break

        # Sum opens_last_30_days
        merged_opens_30_days = sum(link.opens_last_30_days for link in links)

        # Merge tags (union)
        merged_tags = []
        for link in links:
            for tag in link.tags:
                if tag not in merged_tags:
                    merged_tags.append(tag)

        # Prefer first non-None category
        merged_category = None
        for link in links:
            if link.category:
                merged_category = link.category
                break

        # Keep longest notes
        merged_notes = ""
        for link in links:
            if len(link.notes) > len(merged_notes):
                merged_notes = link.notes

        # Prefer first non-None source
        merged_source = None
        for link in links:
            if link.source:
                merged_source = link.source
                break

        # Keep most recent health check data
        merged_link_status = "unknown"
        merged_last_checked = None
        merged_http_status_code = None
        last_checked_values = [link.last_checked for link in links if link.last_checked]
        if last_checked_values:
            most_recent_check = max(last_checked_values)
            for link in links:
                if link.last_checked == most_recent_check:
                    merged_link_status = link.link_status
                    merged_last_checked = link.last_checked
                    merged_http_status_code = link.http_status_code
                    break

        # Use the first link's URL format
        merged_url = links[0].url

        # Create merged link
        merged_link = Link(
            name=merged_name,
            url=merged_url,
            favorite=merged_favorite,
            date_added=merged_date_added,
            last_opened=merged_last_opened,
            open_count=merged_open_count,
            archived=merged_archived,
            # Usage tracking
            first_opened=merged_first_opened,
            favorite_toggle_count=merged_toggle_count,
            last_modified=merged_last_modified,
            time_to_first_open=merged_time_to_first_open,
            opens_last_30_days=merged_opens_30_days,
            # Categorization
            tags=merged_tags,
            category=merged_category,
            # domain will be auto-extracted
            # Metadata
            notes=merged_notes,
            source=merged_source,
            # Link health
            link_status=merged_link_status,
            last_checked=merged_last_checked,
            http_status_code=merged_http_status_code
        )

        return merged_link

    def merge_links_manual(self, link1: Link, link2: Link, user_choice: str,
                          keep_name: Optional[str] = None) -> Link:
        """
        Manually merge two conflicting links based on user choice.

        Args:
            link1: First link
            link2: Second link
            user_choice: "link1", "link2", or "custom"
            keep_name: Custom name if user_choice is "custom"

        Returns:
            Merged link
        """
        # Determine the name to use
        if user_choice == "link1":
            merged_name = link1.name
        elif user_choice == "link2":
            merged_name = link2.name
        elif user_choice == "custom" and keep_name:
            merged_name = keep_name
        else:
            # Fallback
            merged_name = link1.name

        # Merge other fields automatically
        links = [link1, link2]
        merged_link = self._merge_links_auto(links)

        # Override the name with user's choice
        merged_link.name = merged_name

        return merged_link

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for comparison.

        Args:
            url: URL to normalize

        Returns:
            Normalized URL string
        """
        url = url.strip().lower()

        # Add https:// if no protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Remove trailing slash
        if url.endswith('/'):
            url = url[:-1]

        # Remove www. prefix for comparison
        url = url.replace('://www.', '://')

        return url

    def _is_url_name(self, name: str, url: str) -> bool:
        """
        Check if the name is just a URL (not a custom name).

        Args:
            name: Link name
            url: Link URL

        Returns:
            True if name appears to be a URL
        """
        name_lower = name.strip().lower()
        url_lower = url.strip().lower()

        # Check if name starts with http/https
        if name_lower.startswith(('http://', 'https://')):
            return True

        # Check if name is the same as URL (with or without protocol)
        url_without_protocol = url_lower.replace('https://', '').replace('http://', '')
        name_without_protocol = name_lower.replace('https://', '').replace('http://', '')

        if name_without_protocol == url_without_protocol:
            return True

        # Check if name is just the domain
        if '/' not in name_lower and name_lower in url_lower:
            return True

        return False
