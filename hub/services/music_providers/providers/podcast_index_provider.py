"""Podcast Index MusicProvider skeleton."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import MusicProvider


class PodcastIndexProvider(MusicProvider):
    id = "podcast_index"
    label = "Podcast Index"
    kind = "podcast"
    requires_auth = False
    capabilities = frozenset()

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def get_status(self) -> Dict[str, Any]:
        enabled = bool(self.config.get("enabled", True))
        api_key = str(self.config.get("api_key") or "").strip()
        api_secret = str(self.config.get("api_secret") or "").strip()
        configured = bool(api_key and api_secret) if (api_key or api_secret) else True
        message = "Ready" if configured else "Optional API credentials not fully configured."
        return {
            "enabled": enabled,
            "configured": configured,
            "connected": enabled and configured,
            "message": message if enabled else "Podcast Index integration disabled.",
        }
