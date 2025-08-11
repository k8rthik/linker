#!/usr/bin/env python3
"""
Resource Manager for handling file paths in both development and bundled environments.
This ensures data files are correctly located whether running from source or as a Mac app.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional


class ResourceManager:
    """Manages resource and data file paths for bundled and development environments."""
    
    def __init__(self):
        self._is_bundled = self._detect_bundle()
        self._app_support_dir = self._get_app_support_directory()
        self._resource_dir = self._get_resource_directory()
    
    def _detect_bundle(self) -> bool:
        """Detect if running as a bundled Mac app."""
        # Check for py2app bundle
        if hasattr(sys, '_MEIPASS'):  # PyInstaller
            return True
        
        # Check for py2app bundle
        if getattr(sys, 'frozen', False):
            return True
        
        # Check if running from .app bundle
        executable_path = Path(sys.executable)
        return '.app' in str(executable_path)
    
    def _get_app_support_directory(self) -> Path:
        """Get the application support directory for storing user data."""
        if sys.platform == 'darwin':  # macOS
            home = Path.home()
            app_support = home / 'Library' / 'Application Support' / 'Linker'
        else:
            # Fallback for other platforms
            home = Path.home()
            app_support = home / '.linker'
        
        # Create directory if it doesn't exist
        app_support.mkdir(parents=True, exist_ok=True)
        return app_support
    
    def _get_resource_directory(self) -> Path:
        """Get the directory containing bundled resources."""
        if self._is_bundled:
            if hasattr(sys, '_MEIPASS'):  # PyInstaller
                return Path(sys._MEIPASS)
            elif getattr(sys, 'frozen', False):  # py2app
                # For py2app, resources are in the Resources directory
                executable_path = Path(sys.executable)
                return executable_path.parent.parent / 'Resources'
            else:
                # Fallback to executable directory
                return Path(sys.executable).parent
        else:
            # Development environment - use current directory
            return Path.cwd()
    
    def get_data_file_path(self, filename: str) -> Path:
        """
        Get the path for a data file, ensuring it's in the user data directory.
        If running as a bundle and the file doesn't exist in user data,
        copy it from the bundle resources.
        """
        user_file_path = self._app_support_dir / filename
        
        # If file exists in user data directory, use it
        if user_file_path.exists():
            return user_file_path
        
        # If running as bundle, check if file exists in resources and copy it
        if self._is_bundled:
            resource_file_path = self._resource_dir / filename
            if resource_file_path.exists():
                try:
                    shutil.copy2(resource_file_path, user_file_path)
                    print(f"Copied {filename} from bundle to user data directory")
                    return user_file_path
                except Exception as e:
                    print(f"Warning: Could not copy {filename} from bundle: {e}")
        
        # Return user data path (will be created if needed)
        return user_file_path
    
    def get_resource_file_path(self, filename: str) -> Optional[Path]:
        """Get the path for a bundled resource file (read-only)."""
        resource_path = self._resource_dir / filename
        return resource_path if resource_path.exists() else None
    
    def is_bundled(self) -> bool:
        """Check if running as a bundled application."""
        return self._is_bundled
    
    def get_app_support_directory(self) -> Path:
        """Get the application support directory."""
        return self._app_support_dir
    
    def get_resource_directory(self) -> Path:
        """Get the resource directory."""
        return self._resource_dir


# Global instance
_resource_manager = ResourceManager()


def get_data_file_path(filename: str) -> Path:
    """Get the path for a data file."""
    return _resource_manager.get_data_file_path(filename)


def get_resource_file_path(filename: str) -> Optional[Path]:
    """Get the path for a resource file."""
    return _resource_manager.get_resource_file_path(filename)


def is_bundled() -> bool:
    """Check if running as a bundled application."""
    return _resource_manager.is_bundled()


def get_app_support_directory() -> Path:
    """Get the application support directory."""
    return _resource_manager.get_app_support_directory()
