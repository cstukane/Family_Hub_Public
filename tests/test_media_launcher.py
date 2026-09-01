"""
Test script for the Media Launcher Service
"""

import os
import sys

# Add the parent directory to the path so we can import from hub.services
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from hub.services.media_launcher import MediaLauncherService


def test_media_launcher_basic():
    print("Testing Media Launcher Service basic functionality...")

    # Initialize the service
    launcher = MediaLauncherService()

    # Verify basic functionality without actually spawning windows
    print("Service initialized successfully")

    # Check if required methods exist
    assert hasattr(launcher, "spawn_media_window"), "spawn_media_window method missing"
    assert hasattr(launcher, "kill_media_window"), "kill_media_window method missing"
    assert hasattr(launcher, "kill_all_media_windows"), "kill_all_media_windows method missing"
    assert hasattr(launcher, "get_active_windows"), "get_active_windows method missing"

    print("All required methods exist")

    # Check that initial state is empty
    assert len(launcher.media_processes) == 0, "Initial media_processes should be empty"
    assert len(launcher.get_active_windows()) == 0, "Initial active windows should be empty"

    print("Initial state is correct")

    # Test internal helper method exists
    assert hasattr(launcher, "_find_chrome_windows"), "_find_chrome_windows method exists"

    print("All basic tests passed!")


if __name__ == "__main__":
    test_media_launcher_basic()
