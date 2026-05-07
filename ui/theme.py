"""Centralized UI theme tokens — colors, fonts, padding."""

COLORS = {
    "primary": "#2196F3",
    "success": "#4CAF50",
    "warning": "#FFC107",
    "danger": "#F44336",
    "danger_dark": "#a00000",
    "accent_orange": "#FF9800",
    "accent_deep_orange": "#FF5722",
    "accent_purple": "#9C27B0",
    "accent_cyan": "#00BCD4",
    "link": "#0066cc",
    "muted": "#666666",
    "pill_bg": "#e0e0e0",
    "panel_bg": "#f0f0f0",
    "status_active": "#00aa00",
    "status_failed": "#cc0000",
    "status_paused": "#ff9900",
    "status_running": "#0066cc",
}

FONTS = {
    "label_small": ("TkDefaultFont", 8),
    "label_small_bold": ("TkDefaultFont", 8, "bold"),
    "label_bold": ("TkDefaultFont", 9, "bold"),
    "body": ("TkDefaultFont", 10),
    "heading": ("TkDefaultFont", 12, "bold"),
    "title": ("TkDefaultFont", 14, "bold"),
    "title_large": ("", 16, "bold"),
    "body_default_sm": ("", 9),
    "body_default": ("", 10),
    "monospace": ("Courier", 10),
}

PADDING = {
    "default": (20, 20),
    "compact": (10, 10),
    "tight": (5, 5),
}
