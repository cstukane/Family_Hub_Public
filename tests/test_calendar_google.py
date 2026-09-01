"""Tests for the Google Calendar adapter."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from hub.adapters.calendar_google import (
    add_google_event,
    delete_google_event,
    fetch_google_events,
    get_calendar_status,
    get_google_calendar_credentials,
)
from hub.models import CalendarEvent


class TestGoogleCalendarAdapter:
    """Test cases for the Google Calendar adapter."""

    def test_get_google_calendar_credentials_returns_none_if_no_config(self):
        """Test that get_google_calendar_credentials returns None when no config is provided."""
        result = get_google_calendar_credentials(None)
        assert result is None

    @patch("hub.adapters.calendar_google.get_cache")
    def test_fetch_google_events_returns_empty_list_if_no_credentials(self, mock_get_cache):
        """Test that fetch_google_events returns empty list when no credentials available."""
        range_start = datetime(2023, 1, 1)
        range_end = datetime(2023, 1, 31)

        config = {"client_id": "test_id", "client_secret": "test_secret", "calendar_ids": ["primary"]}

        # Mock cache to return None
        mock_get_cache.return_value = None

        with patch("hub.adapters.calendar_google.get_google_calendar_credentials", return_value=None):
            result = fetch_google_events(config, range_start, range_end)
            assert result == []

    def test_add_google_event_returns_none_if_no_credentials(self):
        """Test that add_google_event returns None when no credentials available."""
        config = {"client_id": "test_id", "client_secret": "test_secret", "calendar_ids": ["primary"]}
        title = "Test Event"
        starts_at = datetime(2023, 1, 1, 10, 0)
        ends_at = datetime(2023, 1, 1, 11, 0)

        with patch("hub.adapters.calendar_google.get_google_calendar_credentials", return_value=None):
            result = add_google_event(config, title, starts_at, ends_at)
            assert result is None

    def test_delete_google_event_returns_false_if_no_credentials(self):
        """Test that delete_google_event returns False when no credentials available."""
        config = {"client_id": "test_id", "client_secret": "test_secret", "calendar_ids": ["primary"]}
        event_id = "test_event_id"

        with patch("hub.adapters.calendar_google.get_google_calendar_credentials", return_value=None):
            result = delete_google_event(config, event_id)
            assert result is False

    def test_get_calendar_status_no_credentials(self):
        """Test that get_calendar_status returns proper status when no credentials."""
        config = {"client_id": "test_id", "client_secret": "test_secret", "calendar_ids": ["primary"]}

        with patch("hub.adapters.calendar_google.get_google_calendar_credentials", return_value=None):
            result = get_calendar_status(config)
            expected = {"status": "Google Calendar not authenticated", "source": "Google", "connected": False}
            assert result == expected

    def test_get_calendar_status_with_credentials(self):
        """Test that get_calendar_status returns proper status when authenticated."""
        # Mock credentials object
        mock_credentials = Mock()
        mock_credentials.valid = True

        config = {"client_id": "test_id", "client_secret": "test_secret", "calendar_ids": ["primary"]}

        with patch("hub.adapters.calendar_google.get_google_calendar_credentials", return_value=mock_credentials):
            result = get_calendar_status(config)
            expected = {
                "status": "Google Calendar authenticated and connected",
                "source": "Google",
                "connected": True,
                "calendar_ids": ["primary"],
            }
            assert result == expected

    @patch("hub.adapters.calendar_google.get_cache")
    @patch("hub.adapters.calendar_google.get_google_calendar_credentials")
    @patch("hub.adapters.calendar_google.build")
    def test_add_google_event_success(self, mock_build, mock_get_credentials, mock_get_cache):
        """Test that add_google_event works correctly when credentials are available."""
        # Set up mock credentials
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_get_credentials.return_value = mock_credentials

        # Set up mock service
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_insert = Mock()
        mock_events.insert.return_value = mock_insert

        # Mock the execute method to return a sample event
        mock_insert.execute.return_value = {"id": "test_event_id", "summary": "Test Event", "location": "Test Location"}

        mock_build.return_value = mock_service
        # Mock cache to return None
        mock_get_cache.return_value = None

        config = {"client_id": "test_id", "client_secret": "test_secret", "calendar_ids": ["primary"]}
        title = "Test Event"
        starts_at = datetime(2023, 1, 1, 10, 0)
        ends_at = datetime(2023, 1, 1, 11, 0)
        location = "Test Location"

        result = add_google_event(config, title, starts_at, ends_at, location)

        assert isinstance(result, CalendarEvent)
        assert result.title == "Test Event"
        assert result.location == "Test Location"
        assert result.id == "test_event_id"

        # Verify that the service was called with correct parameters
        mock_build.assert_called_once_with("calendar", "v3", credentials=mock_credentials)
        mock_events.insert.assert_called_once()

    @patch("hub.adapters.calendar_google.set_cache")
    @patch("hub.adapters.calendar_google.get_cache")
    @patch("hub.adapters.calendar_google.get_google_calendar_credentials")
    @patch("hub.adapters.calendar_google.build")
    def test_fetch_google_events_success(self, mock_build, mock_get_credentials, mock_get_cache, mock_set_cache):
        """Test that fetch_google_events works correctly when credentials are available."""
        # Set up mock credentials
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_get_credentials.return_value = mock_credentials

        # Set up mock service
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_list = Mock()
        mock_events.list.return_value = mock_list

        # Mock the execute method to return sample events
        mock_list.execute.return_value = {
            "items": [
                {
                    "id": "event1",
                    "summary": "Test Event 1",
                    "location": "Location 1",
                    "start": {"dateTime": "2023-01-01T10:00:00+00:00"},
                    "end": {"dateTime": "2023-01-01T11:00:00+00:00"},
                }
            ]
        }

        mock_build.return_value = mock_service
        # Mock cache to return None initially to bypass cache check
        mock_get_cache.return_value = None
        # Mock set_cache to do nothing
        mock_set_cache.return_value = None

        config = {"client_id": "test_id", "client_secret": "test_secret", "calendar_ids": ["primary"]}
        range_start = datetime(2023, 1, 1)
        range_end = datetime(2023, 1, 31)

        result = fetch_google_events(config, range_start, range_end)

        assert len(result) == 1
        assert isinstance(result[0], CalendarEvent)
        assert result[0].title == "Test Event 1"
        assert result[0].location == "Location 1"
        assert result[0].id == "event1"

    @patch("hub.adapters.calendar_google.get_cache")
    @patch("hub.adapters.calendar_google.get_google_calendar_credentials")
    @patch("hub.adapters.calendar_google.build")
    def test_delete_google_event_success(self, mock_build, mock_get_credentials, mock_get_cache):
        """Test that delete_google_event works correctly when credentials are available."""
        # Set up mock credentials
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_get_credentials.return_value = mock_credentials

        # Set up mock service
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_delete = Mock()
        mock_events.delete.return_value = mock_delete

        # Mock the execute method
        mock_delete.execute.return_value = None

        mock_build.return_value = mock_service
        # Mock cache to return None
        mock_get_cache.return_value = None

        config = {"client_id": "test_id", "client_secret": "test_secret", "calendar_ids": ["primary"]}
        event_id = "test_event_id"

        result = delete_google_event(config, event_id)

        assert result is True
        mock_build.assert_called_once_with("calendar", "v3", credentials=mock_credentials)
        mock_events.delete.assert_called_once_with(calendarId="primary", eventId=event_id)
