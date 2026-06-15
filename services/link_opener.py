"""Cross-platform local file opener for cached video playback.

The single decision point for online-vs-offline opening lives in
ProfileService.open_links — this module just handles the "fire the system
default app for this file" mechanics.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]

# Extensions QuickTime Player handles and that we want auto-looped.
_VIDEO_EXTS = frozenset({".mp4", ".mov", ".m4v"})

# AppleScript: open in QuickTime with looping enabled, but do not play.
# Multi-open commands (e.g. 3O) would otherwise stack several videos all
# playing at once; the user starts playback themselves with Space on the
# focused window. Looping stays armed so once they hit play, it repeats.
#
# `POSIX file` is resolved *outside* the `tell application` block on
# purpose: inside the tell block, QuickTime returns `missing value` from
# `open`, and the subsequent `set looping of theDoc` fails with -10006.
#
# `activate` is intentionally called *after* `open` so QuickTime is raised
# once the new document's window exists — activating first lets the new
# window land behind whatever was previously frontmost. The trailing
# `set index of window 1 to 1` nudges the just-opened window to the top
# of QuickTime's own window stack so a rapid multi-open doesn't bury it.
_QUICKTIME_LOOP_SCRIPT = """
on run argv
  set thePath to item 1 of argv
  set posixDoc to POSIX file thePath
  tell application "QuickTime Player"
    set theDoc to open posixDoc
    set looping of theDoc to true
    activate
    set index of window 1 to 1
  end tell
end run
"""


def _open_in_quicktime_looping(path: Path) -> None:
    subprocess.run(
        ["osascript", "-e", _QUICKTIME_LOOP_SCRIPT, str(path)],
        check=True,
    )


def open_local_file(path: PathLike) -> bool:
    """Open a local file with the OS default application.

    On macOS, video files are routed through QuickTime Player with looping
    enabled so cached clips replay automatically. Returns True on success,
    False if the file is missing or the OS reports failure. Callers fall
    back to opening the URL on False.
    """
    p = Path(path)
    if not p.exists():
        logger.warning("open_local_file: missing path %s", p)
        return False

    try:
        if sys.platform == "darwin":
            if p.suffix.lower() in _VIDEO_EXTS:
                _open_in_quicktime_looping(p)
            else:
                subprocess.run(["open", str(p)], check=True)
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
