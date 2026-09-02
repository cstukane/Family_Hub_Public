"""SomaFM MusicProvider skeleton."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import MusicProvider


class SomaFmProvider(MusicProvider):
    id = "somafm"
    label = "SomaFM"
    kind = "radio"
    requires_auth = False
    capabilities = frozenset()

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def get_status(self) -> Dict[str, Any]:
        enabled = bool(self.config.get("enabled", True))
        return {
            "enabled": enabled,
            "configured": True,
            "connected": enabled,
            "message": "Ready" if enabled else "SomaFM integration disabled.",
        }
