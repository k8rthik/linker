import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from tkinter import filedialog, messagebox
from models.link import Link
from models.profile import Profile
from services.profile_service import ProfileService


class ImportExportService:
    """Service for importing and exporting links across all profiles."""
    
    def __init__(self, profile_service: ProfileService):
        self._profile_service = profile_service
    
    def export_all_links(self, file_path: Optional[str] = None) -> bool:
        """
        Export all links from all profiles to a simple JSON array.
        Each link includes all its attributes plus the profile name.
        Returns True if successful, False otherwise.
        """
        try:
            # Get all profiles and their links
            all_profiles = self._profile_service.get_all_profiles()
            
            if not all_profiles:
                messagebox.showwarning("Export Warning", "No profiles found to export.")
                return False
            
            # Create flat list of all links with profile information
            all_links = []
            total_links = 0
            
            for profile in all_profiles:
                for link in profile.links:
                    # Get link data and add profile information
                    link_data = link.to_dict()
                    link_data["profile"] = profile.name
                    all_links.append(link_data)
                    total_links += 1
            
            if total_links == 0:
                messagebox.showwarning("Export Warning", "No links found to export.")
                return False
            
            # If no file path provided, show save dialog
            if not file_path:
                file_path = filedialog.asksaveasfilename(
                    title="Export All Links",
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    initialfile=f"linker_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
            
            if not file_path:
                return False  # User cancelled
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(all_links, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo(
                "Export Successful", 
                f"Successfully exported {total_links} links from {len(all_profiles)} profiles to:\n{file_path}"
            )
            return True
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export links: {str(e)}")
            return False
    
    def import_links(self, file_path: Optional[str] = None) -> bool:
        """
        Import links from a JSON array file.
        
        Args:
            file_path: Path to the import file. If None, shows file dialog.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            # If no file path provided, show open dialog
            if not file_path:
                file_path = filedialog.askopenfilename(
                    title="Import Links",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                )
            
            if not file_path:
                return False  # User cancelled
            
            if not os.path.exists(file_path):
                messagebox.showerror("Import Error", f"File not found: {file_path}")
                return False
            
            # Read and validate file
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Validate import data structure
            if not self._validate_import_data(import_data):
                messagebox.showerror("Import Error", "Invalid file format. Please select a valid linker export file.")
                return False
            
            # Show import confirmation with intelligent merging info
            total_links = len(import_data)
            profiles_in_file = set(link.get("profile", "Default") for link in import_data)
            
            confirm_message = f"Import {total_links} links from {len(profiles_in_file)} profiles?\n\n"
            confirm_message += f"Profiles: {', '.join(sorted(profiles_in_file))}\n\n"
            confirm_message += "Import behavior:\n"
            confirm_message += "• New profiles will be created if they don't exist\n"
            confirm_message += "• Duplicate URLs will be intelligently merged\n"
            confirm_message += "• Existing links will be updated with better metadata\n"
            confirm_message += "• No data will be lost or overwritten"
            
            if not messagebox.askyesno("Confirm Import", confirm_message):
                return False
            
            # Perform import
            return self._import_links_simple(import_data)
            
        except json.JSONDecodeError:
            messagebox.showerror("Import Error", "Invalid JSON file format.")
            return False
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import links: {str(e)}")
            return False
    
    def _validate_import_data(self, data: List[Dict[str, Any]]) -> bool:
        """Validate that the import data is a valid array of links."""
        try:
            # Check if data is a list
            if not isinstance(data, list):
                return False
            
            # Check if list is not empty
            if len(data) == 0:
                return False
            
            # Validate each link
            for link_data in data:
                if not isinstance(link_data, dict):
                    return False
                # Check for required link fields
                if "name" not in link_data or "url" not in link_data:
                    return False
            
            return True
        except Exception:
            return False
    
    def _import_links_simple(self, links_data: List[Dict[str, Any]]) -> bool:
        """Import links from a simple array format with intelligent duplicate handling."""
        try:
            imported_links_count = 0
            updated_links_count = 0
            skipped_duplicates_count = 0
            profiles_created = set()
            
            # Group links by profile
            links_by_profile = {}
            for link_data in links_data:
                profile_name = link_data.get("profile", "Default")
                if profile_name not in links_by_profile:
                    links_by_profile[profile_name] = []
                links_by_profile[profile_name].append(link_data)
            
            # Import links into their respective profiles
            for profile_name, links in links_by_profile.items():
                # Check if profile already exists
                existing_profile = self._profile_service._profile_repository.find_by_name(profile_name)
                
                if existing_profile:
                    # Add links to existing profile with duplicate detection
                    for link_data in links:
                        try:
                            # Remove the profile field before creating Link object
                            clean_link_data = {k: v for k, v in link_data.items() if k != "profile"}
                            new_link = Link.from_dict(clean_link_data)
                            
                            # Check for duplicates by URL
                            duplicate_found = False
                            for i, existing_link in enumerate(existing_profile.links):
                                if self._urls_match(existing_link.url, new_link.url):
                                    # Found duplicate - decide how to handle it
                                    conflict_resolution = self._resolve_link_conflict(existing_link, new_link)
                                    if conflict_resolution == "update":
                                        # Update existing link with merged data
                                        merged_link = self._merge_link_data(existing_link, new_link)
                                        existing_profile._links[i] = merged_link
                                        updated_links_count += 1
                                    elif conflict_resolution == "skip":
                                        # Skip the import of this link
                                        skipped_duplicates_count += 1
                                    duplicate_found = True
                                    break
                            
                            if not duplicate_found:
                                # No duplicate found, add new link
                                existing_profile.add_link(new_link)
                                imported_links_count += 1
                                
                        except (ValueError, KeyError) as e:
                            print(f"Skipping invalid link: {e}")
                            continue  # Skip invalid links
                    
                    self._profile_service._profile_repository.update(existing_profile)
                else:
                    # Create new profile
                    profile_links = []
                    for link_data in links:
                        try:
                            # Remove the profile field before creating Link object
                            clean_link_data = {k: v for k, v in link_data.items() if k != "profile"}
                            link = Link.from_dict(clean_link_data)
                            profile_links.append(link)
                            imported_links_count += 1
                        except (ValueError, KeyError) as e:
                            print(f"Skipping invalid link: {e}")
                            continue  # Skip invalid links
                    
                    # Create new profile
                    new_profile = Profile(name=profile_name, links=profile_links)
                    self._profile_service._profile_repository.add(new_profile)
                    profiles_created.add(profile_name)
            
            # Refresh the current view
            self._profile_service._load_current_profile()
            self._profile_service._notify_observers()
            
            # Show detailed success message
            message = f"Import completed:\n"
            message += f"• {imported_links_count} new links added\n"
            if updated_links_count > 0:
                message += f"• {updated_links_count} existing links updated\n"
            if skipped_duplicates_count > 0:
                message += f"• {skipped_duplicates_count} duplicate links skipped\n"
            if profiles_created:
                message += f"• Created {len(profiles_created)} new profiles: {', '.join(sorted(profiles_created))}"
            
            messagebox.showinfo("Import Successful", message)
            return True
            
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import links: {str(e)}")
            return False
    
    def _urls_match(self, url1: str, url2: str) -> bool:
        """Check if two URLs are essentially the same (normalize for comparison)."""
        # Normalize URLs for comparison
        def normalize_url(url: str) -> str:
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
        
        return normalize_url(url1) == normalize_url(url2)
    
    def _resolve_link_conflict(self, existing_link: Link, new_link: Link) -> str:
        """
        Determine how to resolve a conflict between existing and new link.
        Returns: 'update', 'skip', or 'add'
        """
        # If the links are essentially identical, skip
        if (existing_link.name == new_link.name and 
            existing_link.favorite == new_link.favorite):
            return "skip"
        
        # If there are meaningful differences, update with merged data
        return "update"
    
    def _merge_link_data(self, existing_link: Link, new_link: Link) -> Link:
        """
        Intelligently merge data from existing and new link.
        Priority rules:
        - Keep the most descriptive name (longer, non-URL names preferred)
        - Merge favorite status (true if either is true)
        - Keep earliest date_added
        - Keep most recent last_opened
        """
        # Choose the better name (prefer non-URL names and longer names)
        merged_name = existing_link.name
        if (len(new_link.name) > len(existing_link.name) and 
            not new_link.name.startswith(('http://', 'https://'))):
            merged_name = new_link.name
        elif (existing_link.name.startswith(('http://', 'https://')) and 
              not new_link.name.startswith(('http://', 'https://'))):
            merged_name = new_link.name
        
        # Merge favorite status (true if either is true)
        merged_favorite = existing_link.favorite or new_link.favorite
        
        # Keep earliest date_added
        merged_date_added = existing_link.date_added
        if (new_link.date_added and 
            (not existing_link.date_added or new_link.date_added < existing_link.date_added)):
            merged_date_added = new_link.date_added
        
        # Keep most recent last_opened
        merged_last_opened = existing_link.last_opened
        if (new_link.last_opened and 
            (not existing_link.last_opened or new_link.last_opened > existing_link.last_opened)):
            merged_last_opened = new_link.last_opened
        
        # Create merged link
        merged_link = Link(
            name=merged_name,
            url=existing_link.url,  # Keep existing URL format
            favorite=merged_favorite,
            date_added=merged_date_added,
            last_opened=merged_last_opened
        )
        
        return merged_link 