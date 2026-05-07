"""Tests for ui.theme tokens."""

from ui import theme


def test_colors_dict_is_populated():
    assert theme.COLORS
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in theme.COLORS.items())


def test_fonts_dict_is_populated():
    assert theme.FONTS
    assert all(isinstance(v, tuple) and len(v) >= 2 for v in theme.FONTS.values())


def test_padding_dict_is_populated():
    assert theme.PADDING
    assert all(isinstance(v, tuple) and len(v) == 2 for v in theme.PADDING.values())


def test_required_color_keys_exist():
    """Pin the keys that the dialogs/components actually reference."""
    required = {
        "primary", "success", "warning", "danger", "muted",
        "pill_bg", "panel_bg", "link",
        "status_active", "status_failed", "status_paused", "status_running",
    }
    assert required.issubset(theme.COLORS.keys())


def test_required_font_keys_exist():
    required = {
        "label_small", "label_small_bold", "label_bold",
        "body", "heading", "title", "title_large",
        "body_default", "body_default_sm", "monospace",
    }
    assert required.issubset(theme.FONTS.keys())


def test_color_values_are_valid_hex():
    """Every color must be a valid hex string (#RRGGBB or #RGB)."""
    for name, value in theme.COLORS.items():
        assert value.startswith("#"), f"{name}={value!r} should start with #"
        assert len(value) in (4, 7), f"{name}={value!r} not a hex color"
