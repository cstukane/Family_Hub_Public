"""Utility helpers for making Spotify Web API calls using OAuth tokens."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from flask import current_app, has_app_context

from hub.utils.http import RateLimitError, rate_limited_request

from .spotify_auth import SpotifyAuthError, get_valid_access_token, refresh_access_token

API_BASE = "https://api.spotify.com/v1"

COOLDOWN_SECONDS_RATE_LIMIT = 60
COOLDOWN_SECONDS_AUTH = 300
_COOLDOWN_UNTIL = 0.0
_COOLDOWN_REASON = ""
_LAST_COOLDOWN_LOG = 0.0


def _get_logger() -> logging.Logger:
    if has_app_context():
        return current_app.logger
    return logging.getLogger(__name__)


def _set_cooldown(reason: str, seconds: int) -> None:
    global _COOLDOWN_UNTIL, _COOLDOWN_REASON, _LAST_COOLDOWN_LOG
    now = time.monotonic()
    until = now + max(0, seconds)
    if until > _COOLDOWN_UNTIL:
        _COOLDOWN_UNTIL = until
        _COOLDOWN_REASON = reason

    if now - _LAST_COOLDOWN_LOG > 30:
        _get_logger().warning(
            "Spotify requests paused for %ss: %s",
            int(max(0, _COOLDOWN_UNTIL - now)),
            reason,
        )
        _LAST_COOLDOWN_LOG = now


def _ensure_not_in_cooldown() -> None:
    now = time.monotonic()
    if now < _COOLDOWN_UNTIL:
        remaining = int(max(0, _COOLDOWN_UNTIL - now))
        reason = _COOLDOWN_REASON or "cooldown"
        raise SpotifyAuthError(f"Spotify temporarily unavailable ({reason}). Try again in {remaining}s.")


def _ensure_token(spotify_config: Optional[Dict] = None) -> str:
    token = get_valid_access_token(spotify_config)
    if not token:
        raise SpotifyAuthError("Spotify account is not connected.")
    return token


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _request(
    method: str,
    path: str,
    *,
    spotify_config: Optional[Dict] = None,
    expected_status: Union[int, Tuple[int, ...]] = (200, 204),
    retry_on_unauthorized: bool = True,
    **kwargs,
) -> requests.Response:
    if isinstance(expected_status, int):
        expected = (expected_status,)
    else:
        expected = expected_status

    _ensure_not_in_cooldown()
    token = _ensure_token(spotify_config)
    url = f"{API_BASE}{path}"
    headers = kwargs.pop("headers", {})
    headers.update(_headers(token))

    try:
        response = rate_limited_request(
            method,
            url,
            headers=headers,
            timeout=15,
            service_name="spotify",
            **kwargs,
        )
    except RateLimitError as exc:
        _set_cooldown("local rate limit hit", COOLDOWN_SECONDS_RATE_LIMIT)
        raise SpotifyAuthError("Spotify API rate limit exceeded.") from exc
    except requests.RequestException as exc:
        current_app.logger.error("Spotify API request failed: %s %s %s", method, url, exc)
        raise SpotifyAuthError("Unable to reach Spotify at the moment.") from exc

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        try:
            retry_seconds = int(retry_after)
        except (TypeError, ValueError):
            retry_seconds = COOLDOWN_SECONDS_RATE_LIMIT
        _set_cooldown("spotify rate limit (429)", retry_seconds)
        raise SpotifyAuthError("Spotify API rate limit exceeded.")

    if response.status_code == 401 and retry_on_unauthorized:
        refreshed = refresh_access_token(spotify_config)
        if not refreshed:
            _set_cooldown("authorization expired", COOLDOWN_SECONDS_AUTH)
            raise SpotifyAuthError("Spotify session expired. Please reconnect.")
        headers.update(_headers(refreshed.get("access_token")))
        response = rate_limited_request(
            method,
            url,
            headers=headers,
            timeout=15,
            service_name="spotify",
            **kwargs,
        )
        if response.status_code == 401:
            _set_cooldown("authorization expired", COOLDOWN_SECONDS_AUTH)
            raise SpotifyAuthError("Spotify session expired. Please reconnect.")

    if response.status_code not in expected:
        raise SpotifyAuthError(_extract_error_message(response))

    return response


def _extract_error_message(response: requests.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        data = {}

    message = data.get("error")
    if isinstance(message, dict):
        message = message.get("message") or message.get("reason")

    message = message or response.text or "Spotify request failed."
    return f"{message} (HTTP {response.status_code})"


def _format_track(item: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not item:
        return None

    artists = ", ".join(artist.get("name") for artist in item.get("artists", []) if artist.get("name"))
    images = item.get("album", {}).get("images", [])
    album_art = images[0]["url"] if images else None

    return {
        "title": item.get("name"),
        "artist": artists or "Unknown Artist",
        "album": item.get("album", {}).get("name"),
        "duration": int(item.get("duration_ms", 0) / 1000) if item.get("duration_ms") else 0,
        "album_art_url": album_art,
        "spotify_id": item.get("id"),
        "uri": item.get("uri"),
    }


def _simplify_playlist(playlist: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not playlist:
        return None

    images = playlist.get("images") or []
    return {
        "id": playlist.get("id"),
        "name": playlist.get("name"),
        "description": playlist.get("description"),
        "track_count": playlist.get("tracks", {}).get("total"),
        "image_url": images[0]["url"] if images else None,
        "owner": playlist.get("owner", {}).get("display_name"),
        "uri": playlist.get("uri"),
    }


def get_current_playback(spotify_config: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
    """Return the current playback status or None."""
    response = _request("GET", "/me/player", spotify_config=spotify_config, expected_status=(200, 204))
    if response.status_code == 204:
        return None

    payload = response.json()
    track = _format_track(payload.get("item"))

    return {
        "device": payload.get("device"),
        "is_playing": payload.get("is_playing", False),
        "progress_ms": payload.get("progress_ms", 0),
        "track": track,
        "shuffle_state": payload.get("shuffle_state"),
        "repeat_state": payload.get("repeat_state"),
    }


def get_queue(spotify_config: Optional[Dict] = None) -> Dict[str, Any]:
    """Return the upcoming Spotify queue."""
    response = _request("GET", "/me/player/queue", spotify_config=spotify_config)
    payload = response.json()
    queue_items = [track for track in (_format_track(item) for item in payload.get("queue", [])) if track]
    return {
        "currently_playing": _format_track(payload.get("currently_playing")),
        "queue": queue_items,
    }


def play_track_uri(
    track_uri: str,
    *,
    device_id: Optional[str] = None,
    spotify_config: Optional[Dict] = None,
) -> None:
    """Start playback immediately for a single track URI."""
    uri = (track_uri or "").strip()
    if not uri:
        raise SpotifyAuthError("Track URI is required.")

    payload = {"uris": [uri]}
    params = {"device_id": device_id} if device_id else None
    _request(
        "PUT",
        "/me/player/play",
        json=payload,
        params=params,
        spotify_config=spotify_config,
        expected_status=(200, 202, 204),
    )


def enqueue_uri(
    track_uri: str,
    *,
    device_id: Optional[str] = None,
    spotify_config: Optional[Dict] = None,
) -> None:
    """Append a track URI to the Spotify playback queue."""
    uri = (track_uri or "").strip()
    if not uri:
        raise SpotifyAuthError("Track URI is required.")

    params = {"uri": uri}
    if device_id:
        params["device_id"] = device_id
    _request(
        "POST",
        "/me/player/queue",
        params=params,
        spotify_config=spotify_config,
        expected_status=(200, 202, 204),
    )


def reorder_queue_append(
    track_uris: List[str],
    *,
    device_id: Optional[str] = None,
    spotify_config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Best-effort queue reorder for Spotify by appending items in a new order.

    Spotify does not expose queue mutation/reordering APIs, so this appends
    items to the queue in the requested order.
    """
    normalized = []
    seen = set()
    for uri in track_uris or []:
        candidate = (uri or "").strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)

    if not normalized:
        raise SpotifyAuthError("At least one queue URI is required.")

    for uri in normalized[:25]:
        enqueue_uri(uri, device_id=device_id, spotify_config=spotify_config)

    return {
        "ok": True,
        "mode": "append",
        "enqueued_count": min(len(normalized), 25),
    }


def get_devices(spotify_config: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """Return available Spotify Connect devices."""
    response = _request("GET", "/me/player/devices", spotify_config=spotify_config)
    payload = response.json()
    devices = payload.get("devices", [])
    return devices if isinstance(devices, list) else []


def transfer_playback(
    device_id: str,
    *,
    play: bool = True,
    spotify_config: Optional[Dict] = None,
) -> None:
    """Transfer playback to a specific device."""
    payload = {
        "device_ids": [device_id],
        "play": bool(play),
    }
    _request("PUT", "/me/player", json=payload, spotify_config=spotify_config, expected_status=(200, 202, 204))


def resume_playback(device_id: Optional[str] = None, spotify_config: Optional[Dict] = None) -> None:
    params = {"device_id": device_id} if device_id else None
    _request("PUT", "/me/player/play", params=params, spotify_config=spotify_config, expected_status=(200, 204))


def pause_playback(device_id: Optional[str] = None, spotify_config: Optional[Dict] = None) -> None:
    params = {"device_id": device_id} if device_id else None
    _request("PUT", "/me/player/pause", params=params, spotify_config=spotify_config, expected_status=(200, 204))


def next_track(spotify_config: Optional[Dict] = None) -> None:
    _request("POST", "/me/player/next", spotify_config=spotify_config, expected_status=204)


def previous_track(spotify_config: Optional[Dict] = None) -> None:
    _request("POST", "/me/player/previous", spotify_config=spotify_config, expected_status=204)


def seek(position_ms: int, spotify_config: Optional[Dict] = None) -> None:
    params = {"position_ms": position_ms}
    _request("PUT", "/me/player/seek", params=params, spotify_config=spotify_config, expected_status=204)


def set_shuffle(state: bool, device_id: Optional[str] = None, spotify_config: Optional[Dict] = None) -> None:
    params = {
        "state": str(bool(state)).lower(),
    }
    if device_id:
        params["device_id"] = device_id

    _request("PUT", "/me/player/shuffle", params=params, spotify_config=spotify_config, expected_status=204)


def get_user_playlists(limit: int = 10, spotify_config: Optional[Dict] = None) -> List[Dict[str, Any]]:
    params = {
        "limit": max(1, min(limit, 50)),
    }
    response = _request("GET", "/me/playlists", params=params, spotify_config=spotify_config)
    data = response.json()
    playlists = []
    for playlist in data.get("items", []):
        simplified = _simplify_playlist(playlist)
        if simplified:
            playlists.append(simplified)
    return playlists


def get_recent_playlists(limit: int = 10, spotify_config: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """Return playlists ordered by most recently played across devices."""
    limit = max(1, min(limit, 20))
    history_limit = min(max(limit * 3, 20), 50)
    params = {"limit": history_limit}
    try:
        response = _request("GET", "/me/player/recently-played", params=params, spotify_config=spotify_config)
    except SpotifyAuthError as exc:
        message = str(exc).lower()
        if "insufficient client scope" in message or "permission" in message:
            current_app.logger.info(
                "Spotify recent playlists unavailable due to missing scope; falling back to library playlists."
            )
            return get_user_playlists(limit=limit, spotify_config=spotify_config)
        raise
    data = response.json()

    playlist_refs = []
    seen_ids = set()
    for item in data.get("items", []):
        context = item.get("context") or {}
        uri = context.get("uri") or ""
        if not uri.startswith("spotify:playlist:"):
            continue

        playlist_id = uri.split(":")[-1]
        if not playlist_id or playlist_id in seen_ids:
            continue

        seen_ids.add(playlist_id)
        playlist_refs.append((playlist_id, item.get("played_at")))
        if len(playlist_refs) >= limit:
            break

    playlists: List[Dict[str, Any]] = []
    existing_ids = set()
    for playlist_id, played_at in playlist_refs:
        try:
            details = _request("GET", f"/playlists/{playlist_id}", spotify_config=spotify_config)
        except SpotifyAuthError:
            continue

        playlist_data = details.json()
        simplified = _simplify_playlist(playlist_data)
        if not simplified or not simplified.get("id"):
            continue

        simplified["last_played_at"] = played_at
        playlists.append(simplified)
        existing_ids.add(simplified["id"])

    if not playlists:
        return get_user_playlists(limit=limit, spotify_config=spotify_config)

    if len(playlists) < limit:
        fallback = get_user_playlists(limit=limit * 2, spotify_config=spotify_config)
        for extra in fallback:
            extra_id = extra.get("id")
            if not extra_id or extra_id in existing_ids:
                continue
            playlists.append(extra)
            existing_ids.add(extra_id)
            if len(playlists) >= limit:
                break

    return playlists[:limit]


def start_playlist_shuffled(
    playlist_id: str,
    *,
    shuffle: bool = True,
    device_id: Optional[str] = None,
    spotify_config: Optional[Dict] = None,
) -> None:
    if shuffle:
        set_shuffle(True, device_id=device_id, spotify_config=spotify_config)

    context = {
        "context_uri": f"spotify:playlist:{playlist_id}",
    }
    params = {"device_id": device_id} if device_id else None
    _request(
        "PUT",
        "/me/player/play",
        json=context,
        params=params,
        spotify_config=spotify_config,
        expected_status=(200, 202, 204),
    )
