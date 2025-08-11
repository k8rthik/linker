#!/usr/bin/env python3
"""
Minimal script to build a macOS application using PyInstaller.
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

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
    print("Building macOS app with PyInstaller...")
    
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
            '--name=Linker',
            '--onedir',          # Create a directory instead of one file (more reliable)
            '--windowed',        # Hide console
            '--clean',           # Clean cache
            'main_refactored.py'
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("Build completed successfully!")
        
        # Check if app was created
        app_dir = Path('dist/Linker')
        if app_dir.exists():
            print(f"App created at: {app_dir}")
            return True
        else:
            print("App directory not found!")
            return False
            
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

def create_app_bundle():
    """Create a proper .app bundle structure."""
    app_dir = Path('dist/Linker')
    if not app_dir.exists():
        print("Linker directory not found in dist/")
        return False
    
    # Create .app bundle structure
    bundle_dir = Path('dist/Linker.app')
    contents_dir = bundle_dir / 'Contents'
    macos_dir = contents_dir / 'MacOS'
    resources_dir = contents_dir / 'Resources'
    
    # Create directories
    macos_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)
    
    # Move executable to MacOS
    executable = app_dir / 'Linker'
    if executable.exists():
        shutil.move(str(executable), str(macos_dir / 'Linker'))
        print("Moved executable to MacOS directory")
    
    # Move other files to Resources
    for item in app_dir.iterdir():
        if item.name != 'Linker' and item.exists():
            dest = resources_dir / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
    
    # Create Info.plist
    info_plist = contents_dir / 'Info.plist'
    plist_content = '''<?xml version="1.0" encoding="UTF-8"?>
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
    <string>0.2.0</string>
    <key>CFBundleShortVersionString</key>
    <string>0.2.0</string>
    <key>CFBundleExecutable</key>
    <string>Linker</string>
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
    executable_path = macos_dir / 'Linker'
    os.chmod(executable_path, 0o755)
    
    # Remove the old directory
    shutil.rmtree(app_dir)
    
    print(f"Created Linker.app bundle at: {bundle_dir}")
    return True

def main():
    """Main build process."""
    print("=== Minimal macOS App Builder ===")
    print("Building Linker.app for macOS\n")
    
    # Check if PyInstaller is available
    try:
        subprocess.run(['pyinstaller', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
    
    # Clean previous builds
    clean_build()
    
    # Build the app
    if not build_app():
        return 1
    
    # Create .app bundle
    if not create_app_bundle():
        return 1
    
    print("\n=== Build Complete ===")
    print("Linker.app is ready in dist/")
    print("\nTo test:")
    print("1. open dist/Linker.app")
    print("2. Or drag Linker.app to /Applications")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
