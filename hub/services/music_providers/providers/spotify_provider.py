"""Spotify-backed MusicProvider implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from hub.integrations import spotify_auth, spotify_client

from .base import MusicProvider, MusicProviderError


class SpotifyProvider(MusicProvider):
    id = "spotify"
    label = "Spotify"
    kind = "streaming"
    requires_auth = True
    capabilities = frozenset(
        {
            "playback",
            "queue",
            "queue_select",
            "queue_reorder",
            "playlists",
            "seek",
            "shuffle",
            "authorize",
            "devices",
        }
    )

    def _get_config(self) -> Optional[Dict[str, Any]]:
        config = spotify_auth.get_spotify_config()
        return config or None

    def get_status(self) -> Dict[str, Any]:
        status = spotify_auth.get_status()
        status.update(
            {
                "id": self.id,
                "label": self.label,
            }
        )
        return status

    def start_authorization(self) -> Dict[str, Any]:
        return spotify_auth.start_authorization()

    def disconnect(self) -> None:
        spotify_auth.disconnect()

    def resume_playback(self) -> Dict[str, Any]:
        spotify_client.resume_playback(spotify_config=self._get_config())
        return {"ok": True}

    def pause_playback(self) -> Dict[str, Any]:
        spotify_client.pause_playback(spotify_config=self._get_config())
        return {"ok": True}

    def next_track(self) -> Dict[str, Any]:
        spotify_client.next_track(spotify_config=self._get_config())
        return {"ok": True}

    def previous_track(self) -> Dict[str, Any]:
        spotify_client.previous_track(spotify_config=self._get_config())
        return {"ok": True}

    def seek(self, position_ms: int) -> Dict[str, Any]:
        spotify_client.seek(position_ms, spotify_config=self._get_config())
        return {"ok": True}

    def get_current_playback(self) -> Dict[str, Any]:
        playback = spotify_client.get_current_playback(spotify_config=self._get_config())
        return playback or {}

    def get_queue(self) -> Dict[str, Any]:
        return spotify_client.get_queue(spotify_config=self._get_config())

    def play_queue_item(self, track_uri: str) -> Dict[str, Any]:
        spotify_client.play_track_uri(track_uri, spotify_config=self._get_config())
        return {"ok": True}

    def reorder_queue(self, track_uris: List[str]) -> Dict[str, Any]:
        return spotify_client.reorder_queue_append(track_uris, spotify_config=self._get_config())

    def get_playlists(self, limit: int = 20, recent_only: bool = False) -> List[Dict[str, Any]]:
        if recent_only:
            return spotify_client.get_recent_playlists(limit=limit, spotify_config=self._get_config())
        return spotify_client.get_user_playlists(limit=limit, spotify_config=self._get_config())

    def get_devices(self) -> List[Dict[str, Any]]:
        return spotify_client.get_devices(spotify_config=self._get_config())

    def transfer_playback(self, device_id: str, play: bool = True) -> Dict[str, Any]:
        spotify_client.transfer_playback(device_id, play=play, spotify_config=self._get_config())
        return {"ok": True}

    def shuffle_playlist(self, playlist_id: str, shuffle: bool = True) -> Dict[str, Any]:
        if not playlist_id:
            raise MusicProviderError("Playlist ID is required.")
        spotify_client.start_playlist_shuffled(
            playlist_id,
            shuffle=shuffle,
            spotify_config=self._get_config(),
        )
        return {"ok": True}
