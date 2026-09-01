"""
Media Launcher entry point.

This module is a thin shim that delegates to hub/services/media_launcher.py,
which is the canonical implementation.
"""

from hub.services.media_launcher import run_media_launcher_service

if __name__ == "__main__":
    run_media_launcher_service()
