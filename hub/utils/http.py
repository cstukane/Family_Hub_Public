"""HTTP helpers with simple in-process rate limiting for external calls."""

from __future__ import annotations

from collections import deque
from time import monotonic
from typing import Deque, Dict, Optional, Tuple

import requests
from flask import current_app, has_app_context
from requests.adapters import HTTPAdapter

DEFAULT_LIMITS = {
    "alexa": "30 per minute",
    "apple_music": "30 per minute",
    "calendar_ics": "30 per minute",
    "diagnostics": "10 per minute",
    "deezer": "30 per minute",
    "espn": "60 per minute",
    "flickr": "30 per minute",
    "geocode": "10 per minute",
    "google_photos": "30 per minute",
    "homeassistant": "120 per minute",
    "news": "30 per minute",
    "nominatim": "1 per second",
    "openmeteo": "60 per minute",
    "spotify": "60 per minute",
    "sports_ticker": "60 per minute",
    "thesportsdb": "30 per minute",
    "youtube": "30 per minute",
    "webhook": "120 per minute",
}

_FALLBACK_STATE: Dict[str, Deque[float]] = {}
_SESSION: Optional[requests.Session] = None
_SESSION_CONFIG: Optional[Tuple[int, int, int, bool]] = None
_DEFAULT_POOL_CONNECTIONS = 10
_DEFAULT_POOL_MAXSIZE = 10
_DEFAULT_POOL_RETRIES = 0
_DEFAULT_POOL_BLOCK = True


class RateLimitError(RuntimeError):
    """Raised when an external API rate limit is exceeded."""


def rate_limited_request(method: str, url: str, *, service_name: str, **kwargs) -> requests.Response:
    if not acquire_rate_limit(service_name):
        raise RateLimitError(f"Rate limit exceeded for {service_name}")
    session = _get_session()
    return session.request(method, url, **kwargs)


def rate_limited_get(url: str, *, service_name: str, **kwargs) -> requests.Response:
    return rate_limited_request("GET", url, service_name=service_name, **kwargs)


def rate_limited_post(url: str, *, service_name: str, **kwargs) -> requests.Response:
    return rate_limited_request("POST", url, service_name=service_name, **kwargs)


def acquire_rate_limit(service_name: str) -> bool:
    max_calls, period = _get_limit(service_name)
    if max_calls <= 0:
        return True

    state = _get_state()
    window = state.setdefault(service_name, deque())
    now = monotonic()

    while window and now - window[0] > period:
        window.popleft()

    if len(window) >= max_calls:
        return False

    window.append(now)
    return True


def _get_limit(service_name: str) -> Tuple[int, float]:
    override = None
    if has_app_context():
        config = current_app.config.get("CONFIG")
        external_limits = getattr(config, "external_api_limits", None)
        if isinstance(external_limits, dict):
            override = external_limits.get(service_name)

    limit = override or DEFAULT_LIMITS.get(service_name, "60 per minute")
    return _parse_limit(limit)


def _parse_limit(limit: object) -> Tuple[int, float]:
    if isinstance(limit, tuple) and len(limit) == 2:
        return int(limit[0]), float(limit[1])
    if isinstance(limit, dict):
        return int(limit.get("max_calls", 60)), float(limit.get("period_seconds", 60))
    if isinstance(limit, str):
        parts = limit.lower().split()
        if len(parts) >= 3 and parts[1] == "per":
            try:
                max_calls = int(parts[0])
            except ValueError:
                max_calls = 60
            unit = parts[2]
            period = _unit_to_seconds(unit)
            return max_calls, period

    return 60, 60.0


def _unit_to_seconds(unit: str) -> float:
    if unit.startswith("sec"):
        return 1.0
    if unit.startswith("min"):
        return 60.0
    if unit.startswith("hour"):
        return 3600.0
    return 60.0


def _get_state() -> Dict[str, Deque[float]]:
    if has_app_context():
        return current_app.extensions.setdefault("external_rate_limits", {})
    return _FALLBACK_STATE


def _get_session() -> requests.Session:
    global _SESSION
    global _SESSION_CONFIG

    pool_connections, pool_maxsize, pool_retries, pool_block = _get_pool_config()
    config_key = (pool_connections, pool_maxsize, pool_retries, pool_block)

    if _SESSION is None or _SESSION_CONFIG != config_key:
        session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=pool_retries,
            pool_block=pool_block,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _SESSION = session
        _SESSION_CONFIG = config_key

    return _SESSION


def _get_pool_config() -> Tuple[int, int, int, bool]:
    pool_connections = _DEFAULT_POOL_CONNECTIONS
    pool_maxsize = _DEFAULT_POOL_MAXSIZE
    pool_retries = _DEFAULT_POOL_RETRIES
    pool_block = _DEFAULT_POOL_BLOCK

    def _coerce_int(value: object, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _coerce_bool(value: object, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return bool(value)

    if has_app_context():
        config = current_app.config.get("CONFIG")
        pool_config = getattr(config, "http_pool", None) if config else None
        if isinstance(pool_config, dict):
            pool_connections = _coerce_int(pool_config.get("pool_connections", pool_connections), pool_connections)
            pool_maxsize = _coerce_int(pool_config.get("pool_maxsize", pool_maxsize), pool_maxsize)
            pool_retries = _coerce_int(pool_config.get("max_retries", pool_retries), pool_retries)
            pool_block = _coerce_bool(pool_config.get("pool_block", pool_block), pool_block)
        elif pool_config is not None:
            pool_connections = _coerce_int(getattr(pool_config, "pool_connections", pool_connections), pool_connections)
            pool_maxsize = _coerce_int(getattr(pool_config, "pool_maxsize", pool_maxsize), pool_maxsize)
            pool_retries = _coerce_int(getattr(pool_config, "max_retries", pool_retries), pool_retries)
            pool_block = _coerce_bool(getattr(pool_config, "pool_block", pool_block), pool_block)

    return pool_connections, pool_maxsize, pool_retries, pool_block
