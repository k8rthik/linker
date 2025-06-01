from datetime import datetime
from typing import Optional


class DateFormatter:
    """Utility class for formatting dates."""
    
    @staticmethod
    def format_datetime(date_str: Optional[str]) -> str:
        """Format datetime string for display."""
        if not date_str:
            return "Never"
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return "Invalid"
    
    @staticmethod
    def validate_datetime(date_str: str) -> bool:
        """Validate if string is a valid datetime format."""
        try:
            datetime.fromisoformat(date_str)
            return True
        except (ValueError, TypeError):
            return False 