"""Spotify OAuth helpers using Authorization Code Flow with PKCE."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from flask import current_app

from hub.utils.http import RateLimitError, rate_limited_post

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"  # nosec B105
STATE_STORE_KEY = "_SPOTIFY_PKCE_STATES"
TOKEN_FILENAME = "spotify_tokens.json"  # nosec B105
STATE_TTL_SECONDS = 600
DEFAULT_SCOPES = [
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-recently-played",
]


class SpotifyAuthError(RuntimeError):
    """Raised when Spotify authentication fails."""


def _coerce_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return dict(value)


def get_spotify_config(override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return the spotify config as a dict."""
    if override is not None:
        return _coerce_dict(override)

    app_config = current_app.config.get("CONFIG")
    if not app_config:
        return {}

    music_config = getattr(app_config, "music", {})
    music_config = _coerce_dict(music_config)
    spotify_config = music_config.get("spotify") or {}
    return _coerce_dict(spotify_config)


def _normalize_scopes(spotify_config: Dict[str, Any]) -> str:
    scopes = spotify_config.get("scopes") or DEFAULT_SCOPES
    if isinstance(scopes, str):
        scopes = scopes.split()
    scopes = [scope.strip() for scope in scopes if scope and isinstance(scope, str)]
    if not scopes:
        scopes = DEFAULT_SCOPES
    return " ".join(scopes)


def _get_token_path(spotify_config: Dict[str, Any]) -> str:
    configured_path = spotify_config.get("token_cache_path")
    if configured_path:
        if not os.path.isabs(configured_path):
            configured_path = os.path.join(current_app.instance_path, configured_path)
        directory = os.path.dirname(configured_path)
    else:
        directory = current_app.instance_path
        configured_path = os.path.join(directory, TOKEN_FILENAME)

    os.makedirs(directory, exist_ok=True)
    return configured_path


def _load_token_data(spotify_config: Dict[str, Any]) -> Dict[str, Any]:
    token_path = _get_token_path(spotify_config)
    try:
        with open(token_path, "r", encoding="utf-8") as token_file:
            return json.load(token_file)
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError):
        current_app.logger.exception("Failed to read Spotify token cache")
        return {}


def _save_token_data(spotify_config: Dict[str, Any], data: Dict[str, Any]) -> None:
    token_path = _get_token_path(spotify_config)
    with open(token_path, "w", encoding="utf-8") as token_file:
        json.dump(data, token_file)


def _clear_token_data(spotify_config: Dict[str, Any]) -> None:
    token_path = _get_token_path(spotify_config)
    try:
        os.remove(token_path)
    except FileNotFoundError:
        return
    except OSError:
        current_app.logger.warning("Unable to remove Spotify token cache at %s", token_path)


def _store_pkce_state(state: str, verifier: str) -> None:
    store = current_app.config.setdefault(STATE_STORE_KEY, {})
    now = time.time()
    expired = [key for key, meta in store.items() if now - meta["created_at"] > STATE_TTL_SECONDS]
    for key in expired:
        store.pop(key, None)
    store[state] = {"verifier": verifier, "created_at": now}


def _pop_pkce_state(state: str) -> str:
    store = current_app.config.get(STATE_STORE_KEY, {})
    record = store.pop(state, None)
    if not record:
        raise SpotifyAuthError("Invalid or expired OAuth state. Please try again.")
    if time.time() - record["created_at"] > STATE_TTL_SECONDS:
        raise SpotifyAuthError("OAuth state expired. Please restart the flow.")
    return record["verifier"]


def _generate_code_verifier() -> str:
    verifier = base64.urlsafe_b64encode(os.urandom(64)).decode("utf-8")
    return verifier.rstrip("=")


def _generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8")
    return challenge.rstrip("=")


def _validate_redirect_uri(redirect_uri: str) -> None:
    if not redirect_uri:
        raise SpotifyAuthError("Spotify redirect URI is not configured.")
    redirect_uri = redirect_uri.strip()
    if redirect_uri.startswith("https://"):
        return
    if redirect_uri.startswith("http://127."):
        current_app.logger.warning(
            "Using loopback redirect URI %s. Spotify will disallow this for production after migration.",
            redirect_uri,
        )
        return

    raise SpotifyAuthError("Spotify now requires HTTPS redirect URIs. Update your config to use an https:// callback.")


def _build_authorize_params(spotify_config: Dict[str, Any]) -> Dict[str, Any]:
    client_id = spotify_config.get("client_id")
    redirect_uri = spotify_config.get("redirect_uri")
    _validate_redirect_uri(redirect_uri)
    if not client_id:
        raise SpotifyAuthError("Spotify client_id is missing from configuration.")

    verifier = _generate_code_verifier()
    challenge = _generate_code_challenge(verifier)
    state = secrets.token_urlsafe(16)
    _store_pkce_state(state, verifier)

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": _normalize_scopes(spotify_config),
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }

    if spotify_config.get("prompt") == "consent":
        params["show_dialog"] = "true"

    return params


def start_authorization(spotify_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build the Spotify authorization URL."""
    spotify_config = get_spotify_config(spotify_config)
    if not spotify_config.get("enabled", False):
        raise SpotifyAuthError("Spotify integration is disabled in the configuration.")

    params = _build_authorize_params(spotify_config)
    return {
        "authorization_url": f"{AUTH_URL}?{urlencode(params)}",
        "state": params["state"],
    }


def _request_tokens(
    data: Dict[str, Any],
    spotify_config: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        response = rate_limited_post(TOKEN_URL, data=data, timeout=15, service_name="spotify")
    except RateLimitError as exc:
        current_app.logger.error("Spotify token request rate limited: %s", exc)
        raise SpotifyAuthError("Spotify token rate limit exceeded.") from exc
    except requests.RequestException as exc:
        current_app.logger.error("Spotify token request failed: %s", exc)
        raise SpotifyAuthError("Unable to reach Spotify token endpoint.") from exc

    if response.status_code != 200:
        current_app.logger.error("Spotify token endpoint error: %s", response.text)
        raise SpotifyAuthError("Failed to exchange code with Spotify.")

    payload = response.json()
    expires_in = payload.get("expires_in", 3600)
    payload["expires_at"] = int(time.time()) + int(expires_in) - 30  # Renew slightly early

    # Preserve refresh token if Spotify omits it
    existing = _load_token_data(spotify_config)
    if not payload.get("refresh_token") and existing.get("refresh_token"):
        payload["refresh_token"] = existing["refresh_token"]

    _save_token_data(spotify_config, payload)
    return payload


def finish_authorization(
    code: str,
    state: str,
    spotify_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Complete the OAuth exchange after Spotify redirects back."""
    spotify_config = get_spotify_config(spotify_config)
    verifier = _pop_pkce_state(state)
    redirect_uri = spotify_config.get("redirect_uri")
    _validate_redirect_uri(redirect_uri)

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": spotify_config.get("client_id"),
        "code_verifier": verifier,
    }

    client_secret = spotify_config.get("client_secret")
    if client_secret:
        data["client_secret"] = client_secret

    return _request_tokens(data, spotify_config)


def refresh_access_token(spotify_config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Refresh the Spotify access token if we have a refresh token."""
    spotify_config = get_spotify_config(spotify_config)
    tokens = _load_token_data(spotify_config)
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        return None

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": spotify_config.get("client_id"),
    }

    client_secret = spotify_config.get("client_secret")
    if client_secret:
        data["client_secret"] = client_secret

    try:
        return _request_tokens(data, spotify_config)
    except SpotifyAuthError:
        current_app.logger.exception("Failed to refresh Spotify access token")
        _clear_token_data(spotify_config)
        return None


def get_valid_access_token(spotify_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Return a valid access token, refreshing it if necessary."""
    spotify_config = get_spotify_config(spotify_config)
    tokens = _load_token_data(spotify_config)
    access_token = tokens.get("access_token")
    expires_at = tokens.get("expires_at", 0)

    if not access_token:
        return None

    if expires_at <= time.time():
        refreshed = refresh_access_token(spotify_config)
        if not refreshed:
            return None
        return refreshed.get("access_token")

    return access_token


def disconnect(spotify_config: Optional[Dict[str, Any]] = None) -> None:
    """Remove cached Spotify tokens."""
    spotify_config = get_spotify_config(spotify_config)
    _clear_token_data(spotify_config)


def get_status(spotify_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return connection status for the frontend."""
    spotify_config = get_spotify_config(spotify_config)
    enabled = bool(spotify_config.get("enabled"))
    configured = bool(spotify_config.get("client_id")) and bool(spotify_config.get("redirect_uri"))

    tokens = _load_token_data(spotify_config) if enabled and configured else {}
    access_token = tokens.get("access_token")
    expires_at = tokens.get("expires_at")
    scopes = tokens.get("scope") or tokens.get("scopes") or ""
    if isinstance(scopes, str):
        scopes = [scope for scope in scopes.split() if scope]

    status = {
        "enabled": enabled,
        "configured": configured,
        "connected": bool(access_token) and enabled and configured,
        "expires_at": expires_at,
        "has_refresh_token": bool(tokens.get("refresh_token")),
        "scopes": scopes if isinstance(scopes, list) else scopes,
    }

    if not enabled:
        status["message"] = "Spotify integration is disabled."
    elif not configured:
        status["message"] = "Spotify client ID and HTTPS redirect URI are required."
    elif not access_token:
        status["message"] = "Not connected to Spotify."

    return status
