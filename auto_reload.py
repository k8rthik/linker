import sys
import subprocess
import os
from watchgod import watch


def start_app():
    # Launch "main.py" in its own process. Adjust python interpreter if needed.
    print("Launching main.py")
    return subprocess.Popen([sys.executable, "main.py"])


if __name__ == "__main__":
    # Immediately start the Tkinter app the first time.
    proc = start_app()

    # watchgod.watch yields a stream of (changes, path) whenever something under "." changes.
    # You can tweak the "path" or exclude patterns as needed.
    for changes in watch("."):
        # As soon as watchgod detects any file‐change event under ".", this loop body runs.
        print(f"Detected changes: {changes}. Restarting main.py…")

        # Kill the old process cleanly.
        proc.terminate()
        proc.wait()

        # Relaunch the app.
        proc = start_app()
