#!/usr/bin/env python3
"""
Minimal script to build a macOS application using PyInstaller.
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path


def get_version_from_git():
    """
    Get version intelligently from git.

    Returns version string based on:
    1. Latest git tag (if exists)
    2. Tag + commit count + short hash (if commits after tag)
    3. Short hash only (if no tags)
    4. Fallback to __version__.py (if git fails)
    """
    try:
        # Try to get version from git describe
        result = subprocess.run(
            ['git', 'describe', '--tags', '--always', '--dirty'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0 and result.stdout.strip():
            git_version = result.stdout.strip()

            # Clean up the version string
            # Remove 'v' prefix if present
            if git_version.startswith('v'):
                git_version = git_version[1:]

            # If it's just a tag, use it as-is
            # If it has commits after tag (e.g., "0.3.1-5-gabcdef"), keep it
            return git_version

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fallback to __version__.py
    try:
        from __version__ import __version__
        return __version__
    except ImportError:
        pass

    # Ultimate fallback
    return "0.0.0-unknown"


# Get version intelligently
APP_VERSION = get_version_from_git()

def clean_build():
    """Clean previous builds."""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.spec']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}/")
            shutil.rmtree(dir_name)
    
    # Remove spec files
    for spec_file in Path('.').glob('*.spec'):
        spec_file.unlink()

def build_app():
    """Build the macOS app using PyInstaller."""
    app_name = f"Linker-v{APP_VERSION}"
    print(f"Building macOS app with PyInstaller (version {APP_VERSION})...")

    # Temporarily move data files if they exist
    temp_files = []
    for data_file in ['links.json', 'profiles.json']:
        if os.path.exists(data_file):
            temp_name = f"{data_file}.temp"
            shutil.move(data_file, temp_name)
            temp_files.append((data_file, temp_name))
            print(f"Temporarily moved {data_file}")

    try:
        # Run PyInstaller with minimal options
        cmd = [
            'pyinstaller',
            f'--name={app_name}',
            '--onedir',          # Create a directory instead of one file (more reliable)
            '--windowed',        # Hide console
            '--clean',           # Clean cache
            'main_refactored.py'
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        print("Build completed successfully!")

        # Check if app was created
        app_dir = Path(f'dist/{app_name}')
        if app_dir.exists():
            print(f"App created at: {app_dir}")
            return app_name
        else:
            print("App directory not found!")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    
    finally:
        # Restore data files
        for original, temp in temp_files:
            if os.path.exists(temp):
                shutil.move(temp, original)
                print(f"Restored {original}")

def create_app_bundle(app_name):
    """Create a proper .app bundle structure."""
    if not app_name:
        print("No app name provided")
        return False

    app_dir = Path(f'dist/{app_name}')
    if not app_dir.exists():
        print(f"{app_name} directory not found in dist/")
        return False

    # Create .app bundle structure
    bundle_dir = Path(f'dist/{app_name}.app')
    contents_dir = bundle_dir / 'Contents'
    macos_dir = contents_dir / 'MacOS'
    resources_dir = contents_dir / 'Resources'

    # Create directories
    macos_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)

    # Move executable to MacOS
    executable = app_dir / app_name
    if executable.exists():
        shutil.move(str(executable), str(macos_dir / app_name))
        print("Moved executable to MacOS directory")
    
    # Move other files to Resources
    for item in app_dir.iterdir():
        if item.name != app_name and item.exists():
            dest = resources_dir / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    # Create Info.plist
    info_plist = contents_dir / 'Info.plist'
    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Linker</string>
    <key>CFBundleDisplayName</key>
    <string>Linker</string>
    <key>CFBundleIdentifier</key>
    <string>com.local.linker</string>
    <key>CFBundleVersion</key>
    <string>{APP_VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>{APP_VERSION}</string>
    <key>CFBundleExecutable</key>
    <string>{app_name}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSUIElement</key>
    <false/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>'''

    with open(info_plist, 'w') as f:
        f.write(plist_content)

    print("Created Info.plist")

    # Make executable executable
    executable_path = macos_dir / app_name
    os.chmod(executable_path, 0o755)

    # Remove the old directory
    shutil.rmtree(app_dir)

    print(f"Created {app_name}.app bundle at: {bundle_dir}")
    return True

def main():
    """Main build process."""
    print("=== Minimal macOS App Builder ===")
    print(f"Building Linker v{APP_VERSION} for macOS\n")

    # Check if PyInstaller is available
    try:
        subprocess.run(['pyinstaller', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)

    # Clean previous builds
    clean_build()

    # Build the app
    app_name = build_app()
    if not app_name:
        return 1

    # Create .app bundle
    if not create_app_bundle(app_name):
        return 1

    print("\n=== Build Complete ===")
    print(f"{app_name}.app is ready in dist/")
    print("\nTo test:")
    print(f"1. open dist/{app_name}.app")
    print(f"2. Or drag {app_name}.app to /Applications")

    return 0

if __name__ == '__main__':
    sys.exit(main())
