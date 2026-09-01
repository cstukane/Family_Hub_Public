"""Cache utilities for the Kitchen Hub application."""

import json
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from flask import current_app, has_app_context

from hub.db import get_db


class CacheAnalytics:
    """Class to track and analyze cache performance."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0

    def increment_hits(self):
        self.hits += 1

    def increment_misses(self):
        self.misses += 1

    def increment_sets(self):
        self.sets += 1

    def increment_deletes(self):
        self.deletes += 1

    def get_stats(self) -> Dict[str, int]:
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
        }

    def reset_stats(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0


_FALLBACK_CACHE_ANALYTICS = CacheAnalytics()
_DEFAULT_CACHE_LIMITS = {
    "max_entries": 1000,
    "max_size_mb": 50,
}

# Debounce state for _touch_cache_key: avoids a DB write on every cache read.
# last_accessed is only updated once per _TOUCH_INTERVAL_SECONDS per key.
_TOUCH_DEBOUNCE: Dict[str, float] = {}
_TOUCH_DEBOUNCE_LOCK = threading.Lock()
_TOUCH_INTERVAL_SECONDS = 60.0


def get_cache(key: str) -> Optional[Any]:
    """
    Get a value from the cache.

    Args:
        key: Cache key to retrieve

    Returns:
        Cached value if found and not expired, None otherwise
    """
    db = get_db()
    analytics = _get_cache_analytics()

    query = """
        SELECT key, value, updated_at, ttl_seconds
        FROM cache
        WHERE key = ?
    """

    row = db.execute(query, (key,)).fetchone()
    if not row:
        analytics.increment_misses()
        return None

    # Check if the cache entry is expired
    updated_at_val = row["updated_at"]
    # SQLite stores datetime('now') as a naive UTC string; attach UTC so comparisons are aware.
    if isinstance(updated_at_val, str):
        updated_at = datetime.fromisoformat(updated_at_val).replace(tzinfo=timezone.utc)
    elif isinstance(updated_at_val, datetime):
        updated_at = updated_at_val if updated_at_val.tzinfo else updated_at_val.replace(tzinfo=timezone.utc)
    else:
        analytics.increment_misses()
        return None  # Invalid timestamp format

    ttl_seconds = row["ttl_seconds"]

    if ttl_seconds and (datetime.now(timezone.utc) - updated_at).total_seconds() > ttl_seconds:
        # Entry is expired, delete it and return None
        delete_cache(key)
        analytics.increment_misses()
        return None

    try:
        value = json.loads(row["value"])
        _touch_cache_key(db, key)
        analytics.increment_hits()
        return value
    except json.JSONDecodeError:
        analytics.increment_misses()
        return None


def set_cache(key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
    """
    Set a value in the cache.

    Args:
        key: Cache key to store under
        value: Value to cache (will be JSON serialized)
        ttl_seconds: Time to live in seconds. None means no expiration.
    """
    db = get_db()
    analytics = _get_cache_analytics()

    query = """
        INSERT OR REPLACE INTO cache (key, value, updated_at, ttl_seconds, last_accessed)
        VALUES (?, ?, datetime('now'), ?, datetime('now'))
    """

    try:
        value_json = json.dumps(value)
        db.execute(query, (key, value_json, ttl_seconds))
        db.commit()
        analytics.increment_sets()
        _enforce_cache_limits(db)
    except (TypeError, ValueError) as e:
        # Log error if serialization fails
        current_app.logger.error(f"Failed to serialize cache value for key {key}: {e}")


def delete_cache(key: str) -> bool:
    """
    Delete a value from the cache.

    Args:
        key: Cache key to delete

    Returns:
        True if deletion was successful, False otherwise
    """
    db = get_db()
    analytics = _get_cache_analytics()

    query = "DELETE FROM cache WHERE key = ?"
    result = db.execute(query, (key,))
    db.commit()
    analytics.increment_deletes()

    return result.rowcount > 0


def cleanup_expired() -> int:
    """
    Clean up expired cache entries.

    Returns:
        Number of entries removed
    """
    db = get_db()

    query = """
        SELECT key, updated_at, ttl_seconds
        FROM cache
        WHERE ttl_seconds IS NOT NULL
    """

    rows = db.execute(query).fetchall()
    expired_keys = []

    for row in rows:
        updated_at_val = row["updated_at"]
        # SQLite stores datetime('now') as a naive UTC string; attach UTC so comparisons are aware.
        if isinstance(updated_at_val, str):
            updated_at = datetime.fromisoformat(updated_at_val).replace(tzinfo=timezone.utc)
        elif isinstance(updated_at_val, datetime):
            updated_at = updated_at_val if updated_at_val.tzinfo else updated_at_val.replace(tzinfo=timezone.utc)
        else:
            continue  # Skip entries with invalid timestamp format

        ttl_seconds = row["ttl_seconds"]

        if (datetime.now(timezone.utc) - updated_at).total_seconds() > ttl_seconds:
            expired_keys.append(row["key"])

    for key in expired_keys:
        # Use direct DB deletion to avoid recursion
        db.execute("DELETE FROM cache WHERE key = ?", (key,))
    db.commit()

    return len(expired_keys)


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics for performance monitoring.

    Returns:
        Dictionary with cache statistics
    """
    db = get_db()

    # Get total cache entries
    total_entries = db.execute("SELECT COUNT(*) FROM cache").fetchone()[0]

    # Get analytics stats
    analytics_stats = _get_cache_analytics().get_stats()

    # Calculate cache size (approximate)
    size_result = db.execute("SELECT SUM(LENGTH(value)) FROM cache").fetchone()[0]
    size_bytes = size_result if size_result else 0

    return {
        "total_entries": total_entries,
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "analytics": analytics_stats,
    }


def reset_cache_stats():
    """
    Reset cache performance statistics.
    """
    _get_cache_analytics().reset_stats()


def get_cache_keys() -> list:
    """
    Get all cache keys for debugging purposes.

    Returns:
        List of cache keys
    """
    db = get_db()

    rows = db.execute("SELECT key FROM cache").fetchall()
    return [row["key"] for row in rows]


def clear_cache() -> int:
    """
    Clear all cache entries.

    Returns:
        Number of entries removed
    """
    db = get_db()
    analytics = _get_cache_analytics()

    # Count entries before deletion
    count = db.execute("SELECT COUNT(*) FROM cache").fetchone()[0]

    # Delete all entries
    db.execute("DELETE FROM cache")
    db.commit()
    analytics.increment_deletes()

    return count


def clear_weather_cache() -> int:
    """
    Clear only weather cache entries.

    Returns:
        Number of weather entries removed
    """
    db = get_db()
    analytics = _get_cache_analytics()

    # Count weather entries before deletion
    count = db.execute("SELECT COUNT(*) FROM cache WHERE key LIKE 'weather:%'").fetchone()[0]

    # Delete only weather entries
    db.execute("DELETE FROM cache WHERE key LIKE 'weather:%'")
    db.commit()
    analytics.increment_deletes()

    return count


def clear_calendar_cache() -> int:
    """
    Clear only calendar cache entries.

    Returns:
        Number of calendar entries removed
    """
    db = get_db()
    analytics = _get_cache_analytics()

    # Count calendar entries before deletion (keys starting with 'calendar:', 'events:', etc.)
    count = db.execute(
        """
        SELECT COUNT(*) FROM cache
        WHERE key LIKE 'calendar:%' OR key LIKE 'events:%' OR key LIKE 'upcoming:%'
    """
    ).fetchone()[0]

    # Delete only calendar-related entries
    db.execute(
        """
        DELETE FROM cache
        WHERE key LIKE 'calendar:%' OR key LIKE 'events:%' OR key LIKE 'upcoming:%'
    """
    )
    db.commit()
    analytics.increment_deletes()

    return count


def clear_sports_cache() -> int:
    """
    Clear only sports cache entries.

    Returns:
        Number of sports entries removed
    """
    db = get_db()
    analytics = _get_cache_analytics()

    # Count sports entries before deletion (keys starting with 'sports:', 'games:', etc.)
    count = db.execute(
        """
        SELECT COUNT(*) FROM cache
        WHERE key LIKE 'sports:%' OR key LIKE 'games:%' OR key LIKE 'sports_ticker:%'
    """
    ).fetchone()[0]

    # Delete only sports-related entries
    db.execute(
        """
        DELETE FROM cache
        WHERE key LIKE 'sports:%' OR key LIKE 'games:%' OR key LIKE 'sports_ticker:%'
    """
    )
    db.commit()
    analytics.increment_deletes()

    return count


def _get_cache_analytics() -> CacheAnalytics:
    if has_app_context():
        return current_app.extensions.setdefault("cache_analytics", CacheAnalytics())
    return _FALLBACK_CACHE_ANALYTICS


def get_cache_analytics() -> CacheAnalytics:
    """Return the cache analytics instance for the active app context."""
    return _get_cache_analytics()


def _get_cache_limits() -> Tuple[int, int]:
    max_entries = _DEFAULT_CACHE_LIMITS["max_entries"]
    max_size_mb = _DEFAULT_CACHE_LIMITS["max_size_mb"]

    if has_app_context():
        config = current_app.config.get("CONFIG")
        cache_config = getattr(config, "cache", None)
        if cache_config is not None:
            max_entries = getattr(cache_config, "max_entries", max_entries)
            max_size_mb = getattr(cache_config, "max_size_mb", max_size_mb)

    max_entries = int(max_entries) if max_entries is not None else _DEFAULT_CACHE_LIMITS["max_entries"]
    max_size_bytes = int(max_size_mb) * 1024 * 1024 if max_size_mb is not None else 0
    return max_entries, max_size_bytes


def _get_cache_size_bytes(db) -> int:
    size_result = db.execute("SELECT SUM(LENGTH(value)) FROM cache").fetchone()[0]
    return size_result if size_result else 0


def _enforce_cache_limits(db) -> None:
    max_entries, max_size_bytes = _get_cache_limits()
    if max_entries <= 0 and max_size_bytes <= 0:
        return

    total_entries = db.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
    size_bytes = _get_cache_size_bytes(db)

    needs_eviction = (max_entries > 0 and total_entries > max_entries) or (
        max_size_bytes > 0 and size_bytes > max_size_bytes
    )
    if not needs_eviction:
        return

    batch_size = 50
    while True:
        if max_entries > 0 and total_entries > max_entries:
            overage = total_entries - max_entries
        elif max_size_bytes > 0 and size_bytes > max_size_bytes:
            overage = batch_size
        else:
            break

        limit = min(batch_size, overage)
        rows = db.execute(
            """
            SELECT key, LENGTH(value) AS size_bytes
            FROM cache
            ORDER BY COALESCE(last_accessed, updated_at) ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        if not rows:
            break

        keys = [row["key"] for row in rows]
        db.executemany("DELETE FROM cache WHERE key = ?", [(key,) for key in keys])
        db.commit()

        total_entries -= len(keys)
        size_bytes -= sum(row["size_bytes"] or 0 for row in rows)

        if max_entries > 0 and total_entries <= max_entries and (max_size_bytes <= 0 or size_bytes <= max_size_bytes):
            break


def _touch_cache_key(db, key: str) -> None:
    """Update last_accessed for LRU eviction, debounced to at most once per minute per key."""
    now = time.monotonic()
    with _TOUCH_DEBOUNCE_LOCK:
        if now - _TOUCH_DEBOUNCE.get(key, 0.0) < _TOUCH_INTERVAL_SECONDS:
            return
        _TOUCH_DEBOUNCE[key] = now
    try:
        db.execute("UPDATE cache SET last_accessed = datetime('now') WHERE key = ?", (key,))
        db.commit()
    except Exception:
        if has_app_context():
            current_app.logger.debug("Failed to update cache last_accessed for key %s", key)
