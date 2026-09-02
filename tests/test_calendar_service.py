"""Tests for the updated calendar service with Google Calendar support."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from app import create_app
from hub.models import CalendarEvent
from hub.services import calendar


class TestCalendarService:
    """Test cases for the updated calendar service."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config["TESTING"] = True

    @patch("hub.cache.set_cache")
    @patch("hub.cache.get_cache")
    def test_list_events_includes_google_events(self, mock_get_cache, mock_set_cache):
        """Test that list_events includes Google Calendar events when configured."""
        # Mock cache to return None (no cached data)
        mock_get_cache.return_value = None
        # Mock set_cache to do nothing
        mock_set_cache.return_value = None

        # Mock config to use Google Calendar
        mock_config = Mock()
        mock_config.providers = Mock()
        mock_config.providers.calendar = Mock()
        mock_config.providers.calendar.kind = "google"
        mock_config.providers.calendar.google = {
            "client_id": "test_id",
            "client_secret": "test_secret",
            "calendar_ids": ["primary"],
        }

        # Use app context to properly set up the configuration
        with self.app.app_context():
            # Temporarily override the app config
            self.app.config["CONFIG"] = mock_config

            # Mock the Google events function to return some test events
            test_events = [
                CalendarEvent(
                    id=1,
                    title="Test Google Event",
                    starts_at=datetime(2023, 1, 1, 10, 0),
                    ends_at=datetime(2023, 1, 1, 11, 0),
                    source="google",
                )
            ]

            with patch("hub.services.calendar._get_google_events", return_value=test_events):
                with patch("hub.services.calendar._get_local_events", return_value=[]):
                    with patch("hub.services.calendar._get_ics_events", return_value=[]):
                        range_start = datetime(2023, 1, 1)
                        range_end = datetime(2023, 1, 31)

                        result = calendar.list_events(range_start, range_end)

                        assert len(result) == 1
                        assert result[0].title == "Test Google Event"
                        assert result[0].source == "google"

    @patch("hub.cache.set_cache")
    @patch("hub.cache.get_cache")
    def test_add_google_calendar_event_returns_none_if_not_configured(self, mock_get_cache, mock_set_cache):
        """Test that add_google_calendar_event returns None when Google Calendar not configured."""
        # Mock cache to return None
        mock_get_cache.return_value = None
        # Mock set_cache to do nothing
        mock_set_cache.return_value = None

        # Mock config without Google Calendar
        mock_config = Mock()
        mock_config.providers = Mock()
        mock_config.providers.calendar = Mock()
        mock_config.providers.calendar.kind = "ics"  # Not Google
        mock_config.providers.calendar.ics_url = "test_url"

        # Use app context to properly set up the configuration
        with self.app.app_context():
            # Temporarily override the app config
            self.app.config["CONFIG"] = mock_config

            result = calendar.add_google_calendar_event(
                "Test Event", datetime(2023, 1, 1, 10, 0), datetime(2023, 1, 1, 11, 0)
            )
            assert result is None

    @patch("hub.cache.set_cache")
    @patch("hub.cache.get_cache")
    def test_add_google_calendar_event_calls_adapter_on_success(self, mock_get_cache, mock_set_cache):
        """Test that add_google_calendar_event calls the Google adapter."""
        # Mock cache to return None
        mock_get_cache.return_value = None
        # Mock set_cache to do nothing
        mock_set_cache.return_value = None

        # Mock config to use Google Calendar
        mock_config = Mock()
        mock_config.providers = Mock()
        mock_config.providers.calendar = Mock()
        mock_config.providers.calendar.kind = "google"
        mock_config.providers.calendar.google = {
            "client_id": "test_id",
            "client_secret": "test_secret",
            "calendar_ids": ["primary"],
        }

        test_event = CalendarEvent(
            id=1,
            title="Test Google Event",
            starts_at=datetime(2023, 1, 1, 10, 0),
            ends_at=datetime(2023, 1, 1, 11, 0),
            source="google",
        )

        # Use app context to properly set up the configuration
        with self.app.app_context():
            # Temporarily override the app config
            self.app.config["CONFIG"] = mock_config

            with patch("hub.services.calendar.add_google_event", return_value=test_event) as mock_add:
                result = calendar.add_google_calendar_event(
                    "Test Event", datetime(2023, 1, 1, 10, 0), datetime(2023, 1, 1, 11, 0), "Test Location"
                )

                assert result is not None
                assert result.title == "Test Google Event"
                mock_add.assert_called_once()

    def test_get_calendar_status_google_configured(self):
        """Test that get_calendar_status returns Google status when Google is configured."""
        # Mock config to use Google Calendar
        mock_config = Mock()
        mock_config.providers = Mock()
        mock_config.providers.calendar = Mock()
        mock_config.providers.calendar.kind = "google"
        mock_config.providers.calendar.google = {
            "client_id": "test_id",
            "client_secret": "test_secret",
            "calendar_ids": ["primary"],
        }

        expected_status = {
            "status": "Google calendar configured",
            "source": "Google",
            "connected": True,
            "calendar_ids": ["primary"],
        }

        # Use app context to properly set up the configuration
        with self.app.app_context():
            # Temporarily override the app config
            self.app.config["CONFIG"] = mock_config

            with patch("hub.services.calendar.get_google_status", return_value=expected_status):
                result = calendar.get_calendar_status()
                assert result == expected_status

    def test_get_calendar_status_ics_configured(self):
        """Test that get_calendar_status returns ICS status when ICS is configured."""
        # Mock config to use ICS
        mock_config = Mock()
        mock_config.providers = Mock()
        mock_config.providers.calendar = Mock()
        mock_config.providers.calendar.kind = "ics"
        mock_config.providers.calendar.ics_url = "https://example.com/calendar.ics"

        # Use app context to properly set up the configuration
        with self.app.app_context():
            # Temporarily override the app config
            self.app.config["CONFIG"] = mock_config

            result = calendar.get_calendar_status()
            assert "ICS calendar configured" in result["status"]
            assert result["source"] == "ICS"

    def test_get_calendar_status_no_calendar(self):
        """Test that get_calendar_status returns appropriate message when no calendar configured."""
        # Mock config without calendar
        mock_config = Mock()
        mock_config.providers = Mock()
        mock_config.providers.calendar = Mock()
        mock_config.providers.calendar.kind = "none"
        mock_config.providers.calendar.ics_url = None

        # Use app context to properly set up the configuration
        with self.app.app_context():
            # Temporarily override the app config
            self.app.config["CONFIG"] = mock_config

            result = calendar.get_calendar_status()
            assert result["status"] == "Only local events"

    def test_get_google_events_returns_empty_if_no_config(self):
        """Test that _get_google_events returns empty list when no config."""
        # Use app context to properly set up the configuration
        with self.app.app_context():
            # Temporarily override the app config to return None
            self.app.config["CONFIG"] = None

            range_start = datetime(2023, 1, 1)
            range_end = datetime(2023, 1, 31)

            result = calendar._get_google_events(range_start, range_end)
            assert result == []

    def test_get_google_events_returns_empty_if_not_google_kind(self):
        """Test that _get_google_events returns empty list when not Google kind."""
        # Mock config to use non-Google calendar
        mock_config = Mock()
        mock_config.providers = Mock()
        mock_config.providers.calendar = Mock()
        mock_config.providers.calendar.kind = "ics"
        mock_config.providers.calendar.ics_url = "test_url"

        # Use app context to properly set up the configuration
        with self.app.app_context():
            # Temporarily override the app config
            self.app.config["CONFIG"] = mock_config

            range_start = datetime(2023, 1, 1)
            range_end = datetime(2023, 1, 31)

            result = calendar._get_google_events(range_start, range_end)
            assert result == []
