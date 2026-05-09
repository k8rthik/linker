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


def open_local_file(path: PathLike) -> bool:
    """Open a local file with the OS default application.

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
