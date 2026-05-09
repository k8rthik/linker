"""Cross-platform local file opener for cached video playback.

The single decision point for online-vs-offline opening lives in
ProfileService.open_links — this module just handles the "fire the system
default app for this file" mechanics.

On macOS, cached videos are routed to QuickTime Player and entered into
its native fullscreen presentation mode (`present`). Each fullscreened
window gets its own macOS Space — that's the platform's behavior for real
fullscreen and is intentional given how the user batch-opens links.

QuickTime is forced (instead of going through Launch Services) so we can
identify the just-opened document by its cache-hash filename and target
fullscreen on *that* document — no race conditions when ten links open
together. Failures on incompatible files are swallowed so we don't wedge
the calling thread on a single bad file.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


# Open the file in QuickTime, then present (fullscreen) the document
# identified by its basename. Filenames in our cache dir are SHA-prefixed
# hashes, so they're unique per cached video — referring to `document
# theName` instead of `document 1` keeps each script targeting the right
# window even when several osascript invocations are in flight at once.
#
# The 0.3s delay is the minimum needed for QuickTime to materialize the
# document object before we reference it. Both inner blocks are wrapped
# in `try` so that an incompatible file (or a transient glitch) fails
# silently instead of raising and short-circuiting the rest of a batch.
_QUICKTIME_OPEN_FULLSCREEN = '''
on run argv
    set thePath to item 1 of argv
    set theName to do shell script "basename " & quoted form of thePath
    tell application "QuickTime Player"
        activate
        open POSIX file thePath
        delay 0.3
        try
            tell document theName
                play
                present
            end tell
        end try
    end tell
end run
'''


def open_local_file(path: PathLike) -> bool:
    """Open a local file, fullscreening it on macOS via QuickTime.

    Returns True on success, False if the file is missing or the OS
    reports failure. Callers fall back to opening the URL on False.
    """
    p = Path(path)
    if not p.exists():
        logger.warning("open_local_file: missing path %s", p)
        return False

    try:
        if sys.platform == "darwin":
            # 15s timeout: AppleScript usually returns in well under a
            # second. A longer hang means QuickTime is stuck; we'd rather
            # fail and let the caller fall back than block the worker.
            subprocess.run(
                ["osascript", "-e", _QUICKTIME_OPEN_FULLSCREEN, str(p)],
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
