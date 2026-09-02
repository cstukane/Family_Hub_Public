"""Tests for the enhanced cache functionality added in Phase 17."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from hub.cache import (
    cleanup_expired,
    clear_cache,
    delete_cache,
    get_cache,
    get_cache_analytics,
    get_cache_keys,
    get_cache_stats,
    reset_cache_stats,
    set_cache,
)


def test_cache_analytics_initialization():
    """Test cache analytics initialization."""
    analytics = get_cache_analytics()
    assert analytics.hits == 0
    assert analytics.misses == 0
    assert analytics.sets == 0
    assert analytics.deletes == 0


def test_set_cache_increments_counter():
    """Test that set_cache increments the sets counter."""
    with patch("hub.cache.get_db") as mock_get_db, patch("hub.cache._enforce_cache_limits"):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.execute.return_value = mock_db
        mock_db.commit.return_value = None

        # Reset analytics to ensure clean test
        reset_cache_stats()

        set_cache("test_key", "test_value")

        # Check that the sets counter was incremented
        assert get_cache_analytics().sets == 1


def test_get_cache_hit_increments_counter():
    """Test that successful get_cache increments the hits counter."""
    with patch("hub.cache.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock a cache hit
        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda key: {
            "key": "test_key",
            "value": json.dumps("test_value"),
            "updated_at": datetime.now(),
            "ttl_seconds": None,
        }[key]

        mock_db.execute.return_value.fetchone.return_value = mock_row

        # Reset analytics to ensure clean test
        reset_cache_stats()

        result = get_cache("test_key")

        # Check that the hits counter was incremented
        assert result == "test_value"
        assert get_cache_analytics().hits == 1
        assert get_cache_analytics().misses == 0


def test_get_cache_miss_increments_counter():
    """Test that failed get_cache increments the misses counter."""
    with patch("hub.cache.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock a cache miss
        mock_db.execute.return_value.fetchone.return_value = None

        # Reset analytics to ensure clean test
        reset_cache_stats()

        result = get_cache("nonexistent_key")

        # Check that the misses counter was incremented
        assert result is None
        assert get_cache_analytics().hits == 0
        assert get_cache_analytics().misses == 1


def test_delete_cache_increments_counter():
    """Test that delete_cache increments the deletes counter."""
    with patch("hub.cache.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.execute.return_value.rowcount = 1
        mock_db.commit.return_value = None

        # Reset analytics to ensure clean test
        reset_cache_stats()

        delete_cache("test_key")

        # Check that the deletes counter was incremented
        assert get_cache_analytics().deletes == 1


def test_get_cache_stats():
    """Test the get_cache_stats function."""
    with patch("hub.cache.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock execute results
        mock_db.execute.return_value.fetchone.side_effect = [[10], [512000]]  # total entries  # size in bytes (500KB)

        stats = get_cache_stats()

        assert "total_entries" in stats
        assert "size_bytes" in stats
        assert "size_mb" in stats
        assert "analytics" in stats

        assert stats["total_entries"] == 10
        assert stats["size_bytes"] == 512000
        assert stats["analytics"]["hits"] == 0  # Default value from analytics


def test_reset_cache_stats():
    """Test the reset_cache_stats function."""
    reset_cache_stats()
    # Manually increment counters to test reset
    analytics = get_cache_analytics()
    analytics.increment_hits()
    analytics.increment_misses()
    analytics.increment_sets()
    analytics.increment_deletes()

    # Verify counters were incremented
    stats = analytics.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["sets"] == 1
    assert stats["deletes"] == 1

    # Reset stats
    reset_cache_stats()

    # Verify counters are reset to 0
    stats = get_cache_analytics().get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["sets"] == 0
    assert stats["deletes"] == 0


def test_get_cache_keys():
    """Test the get_cache_keys function."""
    with patch("hub.cache.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock execute result
        mock_row = MagicMock()
        mock_row.__getitem__.return_value = "test_key"
        mock_db.execute.return_value.fetchall.return_value = [mock_row]

        keys = get_cache_keys()

        assert isinstance(keys, list)
        assert "test_key" in keys


def test_clear_cache():
    """Test the clear_cache function."""
    with patch("hub.cache.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock execute result to return count before deletion
        mock_db.execute.return_value.fetchone.return_value = [5]
        mock_db.commit.return_value = None

        count = clear_cache()

        # Verify the delete was called and count returned
        assert count == 5
        assert mock_db.execute.called
        assert mock_db.commit.called
