import subprocess
import sys
import webbrowser
from abc import ABC, abstractmethod


class BrowserService(ABC):
    """Abstract interface for browser operations."""
    
    @abstractmethod
    def open_url(self, url: str) -> bool:
        """Open URL in browser. Returns True if successful."""
        pass


class SystemBrowserService(BrowserService):
    """System browser service implementation."""
    
    def open_url(self, url: str) -> bool:
        """Open URL in browser. Returns True if successful."""
        if not url:
            return False
        
        formatted_url = self._format_url(url)
        
        # Try webbrowser first
        if webbrowser.open_new_tab(formatted_url):
            return True

        # Fallback to OS-specific commands
        try:
            if sys.platform == "darwin":
                subprocess.check_call(["open", formatted_url])
            elif sys.platform.startswith("linux"):
                subprocess.check_call(["xdg-open", formatted_url])
            elif sys.platform.startswith("win"):
                subprocess.check_call(["start", formatted_url], shell=True)
            return True
        except Exception:
            return False
    
    def _format_url(self, url: str) -> str:
        """Format URL with proper protocol prefix."""
        if not url.startswith(("http://", "https://")):
            return f"https://{url}"
        return url 