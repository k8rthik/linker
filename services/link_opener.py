"""Cross-platform local file opener for cached video playback.

The single decision point for online-vs-offline opening lives in
ProfileService.open_links — this module just handles the "fire the system
default app for this file" mechanics.

On macOS, cached videos open in QuickTime Player with the window *zoomed*
(maximized to the screen) rather than entered into full-screen. Real
full-screen creates a separate macOS Space per window, which is unusable when
the user opens 10+ links at once. Zoom is the option+green-button behavior:
fills the visible screen without leaving the current Space.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


# AppleScript embedded as a one-shot. The path is passed as argv to avoid
# any string-escaping risk; AppleScript variable substitution handles paths
# with quotes, spaces, and unicode safely. The 0.2s delay gives QuickTime
# time to actually materialize the window before we ask to zoom it — without
# it, `window 1` resolves to nothing on cold launches.
_QUICKTIME_OPEN_ZOOMED = '''
on run argv
    set thePath to item 1 of argv
    tell application "QuickTime Player"
        activate
        open POSIX file thePath
        delay 0.3
        try
            tell document 1 to play
        end try
        try
            tell window 1 to set zoomed to true
        end try
    end tell
end run
'''


def open_local_file(path: PathLike) -> bool:
    """Open a local file with the OS default application.

    On macOS, cached video files open in QuickTime Player and the window is
    zoomed to fit the screen. Other platforms get plain xdg-open / startfile.

    Returns True on success, False if the file is missing or the OS reports
    failure. Callers fall back to opening the URL on False.
    """
    p = Path(path)
    if not p.exists():
        logger.warning("open_local_file: missing path %s", p)
        return False

    try:
        if sys.platform == "darwin":
            # 15s timeout: AppleScript is fast even under load, but if QT is
            # frozen we'd rather fail and let the caller fall back to URL than
            # wedge the calling thread indefinitely.
            subprocess.run(
                ["osascript", "-e", _QUICKTIME_OPEN_ZOOMED, str(p)],
                check=True,
                timeout=15,
            )
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
