"""Cross-platform local file opener for cached video playback.

The single decision point for online-vs-offline opening lives in
ProfileService.open_links — this module just handles the "fire the system
default app for this file" mechanics.

On macOS, cached videos open via Launch Services (`open`) so the user's
default video player handles the file. We then fire a best-effort AppleScript
that zooms (fit-to-screen) the frontmost app's window via the Window > Zoom
menu — the same action as option-clicking the green button. This avoids real
full-screen, which on macOS creates a separate Space per window and breaks
down for batch opens of 10+ links. The zoom is fire-and-forget: failures
(missing menu item, accessibility permission denied, app already zoomed) do
not affect open success.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


# Async zoom: walks the menu bar of whichever app received the file and clicks
# Window > Zoom. The 0.5s delay covers the gap between Launch Services telling
# the app to open and the app actually becoming frontmost with a window. Both
# layers wrapped in `try` so a missing menu item fails silently.
_ZOOM_FRONTMOST_SCRIPT = '''
delay 0.5
tell application "System Events"
    try
        set frontApp to name of first application process whose frontmost is true
        tell process frontApp
            try
                click menu item "Zoom" of menu "Window" of menu bar 1
            end try
        end tell
    end try
end tell
'''


def _zoom_frontmost_window_async() -> None:
    """Fire-and-forget zoom of whichever app just became frontmost.

    Runs in a separate process so a script error or missing accessibility
    permission has no effect on the open path.
    """
    try:
        subprocess.Popen(
            ["osascript", "-e", _ZOOM_FRONTMOST_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as e:
        logger.debug("zoom helper failed to spawn: %s", e)


def open_local_file(path: PathLike) -> bool:
    """Open a local file with the OS default application.

    On macOS, also fires an async zoom of the frontmost app window so videos
    fill the screen without entering real full-screen (which would create a
    Space per video). Other platforms get plain xdg-open / startfile.

    Returns True on success, False if the file is missing or the OS reports
    failure. Callers fall back to opening the URL on False.
    """
    p = Path(path)
    if not p.exists():
        logger.warning("open_local_file: missing path %s", p)
        return False

    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(p)], check=True)
            _zoom_frontmost_window_async()
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(p)], check=True)
        elif sys.platform.startswith("win"):
            # os.startfile is the canonical Windows API but lives on os, not subprocess.
            import os

            os.startfile(str(p))  # type: ignore[attr-defined]
        else:
            logger.warning("open_local_file: unsupported platform %s", sys.platform)
            return False
        return True
    except (subprocess.SubprocessError, OSError) as e:
        logger.warning("open_local_file failed for %s: %s", p, e)
        return False
