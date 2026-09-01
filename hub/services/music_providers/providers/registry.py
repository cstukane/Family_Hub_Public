"""Registry for available music providers."""

from __future__ import annotations

from typing import Dict, List, Optional

from flask import current_app

from ..provider_state import get_active_provider_id, set_active_provider_id
from .base import MusicProvider
from .podcast_index_provider import PodcastIndexProvider
from .radio_browser_provider import RadioBrowserProvider
from .somafm_provider import SomaFmProvider
from .spotify_provider import SpotifyProvider


def _as_dict(value) -> Dict[str, object]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        return dumped if isinstance(dumped, dict) else {}
    if hasattr(value, "dict"):
        dumped = value.dict()
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _get_music_config() -> Dict[str, object]:
    config = current_app.config.get("CONFIG", {})
    if isinstance(config, dict):
        return _as_dict(config.get("music", {}))
    return _as_dict(getattr(config, "music", {}))


def _is_enabled(provider_config: Dict[str, object], default: bool = False) -> bool:
    value = provider_config.get("enabled", default)
    return bool(value)


def _build_providers() -> Dict[str, MusicProvider]:
    """Instantiate providers based on configuration."""
    music_config = _get_music_config()

    providers: Dict[str, MusicProvider] = {}

    spotify_config = _as_dict(music_config.get("spotify", {}))
    if _is_enabled(spotify_config, default=True):
        providers[SpotifyProvider.id] = SpotifyProvider()

    # Provider-specific settings can live under either:
    # 1) music.providers.<provider_id>
    # 2) music.<provider_id> (legacy-friendly fallback)
    providers_config = _as_dict(music_config.get("providers", {}))

    radio_config = _as_dict(providers_config.get("radio_browser", music_config.get("radio_browser", {})))
    if _is_enabled(radio_config, default=False):
        providers[RadioBrowserProvider.id] = RadioBrowserProvider(radio_config)

    somafm_config = _as_dict(providers_config.get("somafm", music_config.get("somafm", {})))
    if _is_enabled(somafm_config, default=False):
        providers[SomaFmProvider.id] = SomaFmProvider(somafm_config)

    podcast_config = _as_dict(providers_config.get("podcast_index", music_config.get("podcast_index", {})))
    if _is_enabled(podcast_config, default=False):
        providers[PodcastIndexProvider.id] = PodcastIndexProvider(podcast_config)

    return providers


def list_providers() -> List[MusicProvider]:
    """Return all configured providers."""
    return list(_build_providers().values())


def get_provider(provider_id: str) -> Optional[MusicProvider]:
    if not provider_id:
        return None
    return _build_providers().get(provider_id)


def get_active_provider() -> Optional[MusicProvider]:
    providers = _build_providers()
    if not providers:
        return None

    active_id = get_active_provider_id()
    if active_id and active_id in providers:
        return providers[active_id]

    # Default to Spotify if present, otherwise the first provider
    default_id = "spotify" if "spotify" in providers else next(iter(providers))
    set_active_provider_id(default_id)
    return providers[default_id]


def set_active_provider(provider_id: str) -> MusicProvider:
    providers = _build_providers()
    if provider_id not in providers:
        raise ValueError(f"Unknown music provider '{provider_id}'.")
    set_active_provider_id(provider_id)
    return providers[provider_id]
