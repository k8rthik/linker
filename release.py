#!/usr/bin/env python3
"""
Release script for linker application.

This script helps create new releases by:
1. Validating the current state
2. Updating version information
3. Creating git tags
4. Generating release artifacts
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from __version__ import __version__


def run_command(cmd, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Exit code: {e.returncode}")
        print(f"Error: {e.stderr}")
        sys.exit(1)


def check_git_status():
    """Check if git working directory is clean."""
    stdout, _ = run_command("git status --porcelain")
    if stdout:
        print("Warning: Working directory is not clean.")
        print("Uncommitted changes:")
        print(stdout)
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)


def check_existing_tag(version):
    """Check if a tag already exists for this version."""
    stdout, _ = run_command(f"git tag -l v{version}", check=False)
    if stdout:
        print(f"Error: Tag v{version} already exists!")
        sys.exit(1)


def create_release_notes():
    """Extract release notes from CHANGELOG.md for current version."""
    if not os.path.exists("CHANGELOG.md"):
        print("Warning: No CHANGELOG.md found")
        return "No release notes available."
    
    with open("CHANGELOG.md", "r") as f:
        content = f.read()
    
    # Extract the section for the current version
    lines = content.split('\n')
    current_version_section = []
    in_current_version = False
    
    for line in lines:
        if line.startswith(f"## [{__version__}]"):
            in_current_version = True
            continue
        elif line.startswith("## [") and in_current_version:
            break
        elif in_current_version:
            current_version_section.append(line)
    
    return '\n'.join(current_version_section).strip()


def create_git_tag():
    """Create a git tag for the current version."""
    release_notes = create_release_notes()
    
    # Create annotated tag
    tag_message = f"Release v{__version__}\n\n{release_notes}"
    
    # Write tag message to temporary file
    with open(".tag_message.tmp", "w") as f:
        f.write(tag_message)
    
    try:
        run_command(f"git tag -a v{__version__} -F .tag_message.tmp")
        print(f"✅ Created git tag v{__version__}")
    finally:
        # Clean up temporary file
        if os.path.exists(".tag_message.tmp"):
            os.remove(".tag_message.tmp")


def create_release_archive():
    """Create a release archive."""
    archive_name = f"linker-v{__version__}.tar.gz"
    
    # Create archive excluding development files
    exclude_patterns = [
        "--exclude=.git",
        "--exclude=.venv",
        "--exclude=__pycache__",
        "--exclude=*.pyc",
        "--exclude=.DS_Store",
        "--exclude=profiles.json",
        "--exclude=links.json",
        "--exclude=*.backup",
        "--exclude=.tag_message.tmp"
    ]
    
    exclude_str = " ".join(exclude_patterns)
    run_command(f"tar -czf {archive_name} {exclude_str} .")
    
    print(f"✅ Created release archive: {archive_name}")
    return archive_name


def show_release_summary():
    """Show a summary of the release."""
    print("\n" + "="*50)
    print(f"🎉 RELEASE SUMMARY - linker v{__version__}")
    print("="*50)
    print(f"📦 Version: {__version__}")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show commits since last tag
    stdout, _ = run_command("git describe --tags --abbrev=0", check=False)
    if stdout:
        last_tag = stdout
        print(f"📝 Changes since {last_tag}:")
        stdout, _ = run_command(f"git log {last_tag}..HEAD --oneline")
        for line in stdout.split('\n'):
            if line:
                print(f"   • {line}")
    
    print("\n🚀 Next steps:")
    print(f"   • Push tags: git push origin v{__version__}")
    print(f"   • Create GitHub release with generated archive")
    print(f"   • Update distribution channels if applicable")


def main():
    """Main release process."""
    print(f"🔄 Creating release for linker v{__version__}")
    
    # Validation steps
    print("📋 Validating release conditions...")
    check_git_status()
    check_existing_tag(__version__)
    
    # Create release artifacts
    print("🏗️  Creating release artifacts...")
    create_git_tag()
    archive_name = create_release_archive()
    
    # Show summary
    show_release_summary()
    
    print(f"\n✅ Release v{__version__} created successfully!")
    print(f"📁 Archive: {archive_name}")


if __name__ == "__main__":
    main()
