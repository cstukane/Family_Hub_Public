"""Tests for the scheduler module."""

from unittest.mock import MagicMock, patch

from hub.scheduler import cleanup_expired_cache, create_scheduler, refresh_calendar_data, refresh_weather_data


def test_create_scheduler(app):
    """Test creating the scheduler."""
    # Test that scheduler can be created without errors
    scheduler = create_scheduler(app)

    # Verify scheduler was created
    assert scheduler is not None

    # Verify expected jobs were added
    job_ids = [job.id for job in scheduler.get_jobs()]
    expected_jobs = ["weather_refresh", "calendar_refresh", "cache_cleanup"]

    for expected_job in expected_jobs:
        assert expected_job in job_ids

    # Shut down the scheduler after test
    if scheduler.running:
        scheduler.shutdown()


def test_refresh_weather_data(app):
    """Test refreshing weather data."""
    with app.app_context():
        # Mock the weather service to avoid external API calls during tests
        with patch("hub.scheduler.weather.get_weather_data") as mock_get_weather:
            mock_get_weather.return_value = {
                "current": {},
                "hourly": [],
                "daily": [],
                "last_updated": "2023-01-01T00:00:00",
            }

            # Call the refresh function
            refresh_weather_data(app)

            # Verify weather service was called
            mock_get_weather.assert_called_once()


def test_refresh_calendar_data(app):
    """Test refreshing calendar data."""
    with app.app_context():
        # Mock the calendar service to avoid external API calls during tests
        with patch("hub.scheduler.calendar.list_events") as mock_list_events:
            from datetime import datetime, timedelta

            mock_list_events.return_value = []

            # Call the refresh function
            refresh_calendar_data(app)

            # Verify calendar service was called
            assert mock_list_events.called
            # Should be called with date range parameters
            args, kwargs = mock_list_events.call_args
            assert len(args) >= 2  # range_start and range_end


def test_cleanup_expired_cache(app):
    """Test cleaning up expired cache entries."""
    with app.app_context():
        # Mock the cleanup_expired function from cache module
        with patch("hub.cache.cleanup_expired") as mock_cleanup:
            mock_cleanup.return_value = 5  # Simulate 5 entries removed

            # Call the cleanup function
            cleanup_expired_cache(app)

            # Verify cleanup function was called
            mock_cleanup.assert_called_once()


def test_dormant_jobs_require_explicit_enablement(app):
    config = app.config["CONFIG"]
    config.services.update_checks = True
    config.services.weather_alerts = True
    config.services.webhooks = True
    config.webhooks = [{"name": "test", "url": "https://example.com/hook", "active": True}]
    config.casting.enabled = True
    config.casting.discovery_enabled = True

    scheduler = create_scheduler(app)
    job_ids = {job.id for job in scheduler.get_jobs()}
    assert {"update_check", "weather_alert_monitor", "webhook_status_check", "casting_device_discovery"} <= job_ids
