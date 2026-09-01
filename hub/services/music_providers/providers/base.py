"""Base classes and shared helpers for music providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Sequence, Set


class MusicProviderError(Exception):
    """Raised when a provider fails to perform an action."""


class MusicProvider(ABC):
    """Abstract base class implemented by each music source."""

    id: str
    label: str
    kind: str = "streaming"  # e.g., streaming | radio | podcast
    requires_auth: bool = False
    capabilities: Set[str] = frozenset()

    def serialize_metadata(self) -> Dict[str, Any]:
        """Return provider metadata suitable for API responses."""
        status = {}
        try:
            status = self.get_status()
        except Exception:
            # Avoid breaking provider listing if status fails
            status = {"connected": False, "error": "Status unavailable"}

        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "requires_auth": self.requires_auth,
            "capabilities": sorted(self.capabilities),
            "status": status,
        }

    # --- Status / Auth ---
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return current connection status."""

    def start_authorization(self) -> Dict[str, Any]:
        """Begin provider authorization (if supported)."""
        raise MusicProviderError("Authorization is not supported for this provider.")

    def disconnect(self) -> None:
        """Disconnect / revoke provider access."""
        raise MusicProviderError("Disconnect is not supported for this provider.")

    # --- Playback commands ---
    def resume_playback(self) -> Dict[str, Any]:
        raise MusicProviderError("Resume playback is not supported.")

    def pause_playback(self) -> Dict[str, Any]:
        raise MusicProviderError("Pause playback is not supported.")

    def next_track(self) -> Dict[str, Any]:
        raise MusicProviderError("Next track is not supported.")

    def previous_track(self) -> Dict[str, Any]:
        raise MusicProviderError("Previous track is not supported.")

    def seek(self, position_ms: int) -> Dict[str, Any]:
        raise MusicProviderError("Seek is not supported.")

    def get_current_playback(self) -> Dict[str, Any]:
        raise MusicProviderError("Playback status is not supported.")

    def get_queue(self) -> Dict[str, Any]:
        raise MusicProviderError("Queue is not supported.")

    def play_queue_item(self, track_uri: str) -> Dict[str, Any]:
        raise MusicProviderError("Selecting a queue item is not supported.")

    def reorder_queue(self, track_uris: Sequence[str]) -> Dict[str, Any]:
        raise MusicProviderError("Queue reordering is not supported.")

    # --- Library helpers ---
    def get_playlists(self, limit: int = 20, recent_only: bool = False) -> Sequence[Dict[str, Any]]:
        raise MusicProviderError("Playlists are not supported.")

    def shuffle_playlist(self, playlist_id: str, shuffle: bool = True) -> Dict[str, Any]:
        raise MusicProviderError("Playlist shuffle is not supported.")

    # --- Utility ---
    def supports(self, capability: str) -> bool:
        return capability in self.capabilities
