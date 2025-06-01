import os
import subprocess
import sys

from watchfiles import watch


def start_app():
    # Launch "main.py" in its own process. Adjust python interpreter if needed.
    print("Launching main.py")
    return subprocess.Popen([sys.executable, "main.py"])


if __name__ == "__main__":
    # Immediately start the Tkinter app the first time.
    proc = start_app()

    # watchfiles.watch yields a stream of sets of (change_type, file_path) tuples whenever something under "." changes.
    for changes in watch("."):
        # Check if any changed file is not "links.json"
        non_data_changes = [
            fp for change_type, fp in changes if os.path.basename(fp) != "links.json"
        ]
        if not non_data_changes:
            # Only links.json changed; skip restarting
            print("Detected change in links.json only; ignoring.")
            continue

        print(
            f"Changes detected (excluding links.json): {non_data_changes}. Restarting main.py…"
        )

        # Kill the old process cleanly.
        proc.terminate()
        proc.wait()

        # Relaunch the app.
        proc = start_app()
