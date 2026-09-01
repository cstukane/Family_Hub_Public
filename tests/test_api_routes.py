"""Tests for the new API routes related to Google Calendar.

Note: Home Assistant integration is dormant in the Public Edition and is not
covered by active tests.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from app import create_app
from hub.models import CalendarEvent


class TestGoogleCalendarAPIRoutes:
    """Test cases for the Google Calendar API routes."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.client = self.app.test_client()

        # Create a test config with Google Calendar settings
        mock_config = Mock()
        mock_config.providers.calendar.kind = "google"
        mock_config.providers.calendar.google = {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "calendar_ids": ["primary"],
        }

        # Temporarily override the app config
        self.app.config["CONFIG"] = mock_config

    @patch("hub.services.calendar.add_google_calendar_event")
    def test_create_google_calendar_event_success(self, mock_add_event):
        """Test creating a Google Calendar event successfully."""
        # Mock the service function to return a test event
        mock_event = CalendarEvent(
            id=1,
            title="Test Event",
            starts_at=datetime(2023, 1, 1, 10, 0),
            ends_at=datetime(2023, 1, 1, 11, 0),
            location="Test Location",
            source="google",
        )
        mock_add_event.return_value = mock_event

        # Prepare test data
        event_data = {
            "title": "Test Event",
            "starts_at": "2023-01-01T10:00:00+00:00",
            "ends_at": "2023-01-01T11:00:00+00:00",
            "location": "Test Location",
        }

        # Make the request
        response = self.client.post(
            "/api/calendar/google", data=json.dumps(event_data), content_type="application/json"
        )

        # Assert the response
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data["title"] == "Test Event"
        assert response_data["location"] == "Test Location"

    @patch("hub.services.calendar.add_google_calendar_event")
    def test_create_google_calendar_event_fails(self, mock_add_event):
        """Test creating a Google Calendar event fails when service returns None."""
        # Mock the service function to return None
        mock_add_event.return_value = None

        # Prepare test data
        event_data = {
            "title": "Test Event",
            "starts_at": "2023-01-01T10:00:00+00:00",
            "ends_at": "2023-01-01T11:00:00+00:00",
            "location": "Test Location",
        }

        # Make the request
        response = self.client.post(
            "/api/calendar/google", data=json.dumps(event_data), content_type="application/json"
        )

        # Assert the response
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert "error" in response_data

    def test_create_google_calendar_event_invalid_dates(self):
        """Test creating a Google Calendar event fails with invalid dates."""
        # Prepare test data with invalid date format
        event_data = {
            "title": "Test Event",
            "starts_at": "invalid-date",
            "ends_at": "invalid-date",
            "location": "Test Location",
        }

        # Make the request
        response = self.client.post(
            "/api/calendar/google", data=json.dumps(event_data), content_type="application/json"
        )

        # Assert the response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Invalid date format" in response_data["error"]

    def test_create_google_calendar_event_no_config(self):
        """Test creating a Google Calendar event fails when not configured."""
        # Create a config without Google Calendar
        mock_config = Mock()
        mock_config.providers.calendar.kind = "ics"
        mock_config.providers.calendar.ics_url = "https://example.com/calendar.ics"
        self.app.config["CONFIG"] = mock_config

        # Prepare test data
        event_data = {
            "title": "Test Event",
            "starts_at": "2023-01-01T10:00:00+00:00",
            "ends_at": "2023-01-01T11:00:00+00:00",
            "location": "Test Location",
        }

        # Make the request
        response = self.client.post(
            "/api/calendar/google", data=json.dumps(event_data), content_type="application/json"
        )

        # Assert the response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Google Calendar not configured" in response_data["error"]

    @patch("google_auth_oauthlib.flow.Flow")
    def test_google_calendar_auth_initiates_oauth(self, mock_flow_class):
        """Test that Google Calendar auth endpoint initiates OAuth flow."""
        # Mock the flow class and its methods
        mock_flow_instance = Mock()
        mock_flow_instance.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth", "state")
        mock_flow_class.from_client_config.return_value = mock_flow_instance

        # Make the request
        response = self.client.get("/api/oauth/google")

        # Assert the response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "auth_url" in response_data
        assert "accounts.google.com" in response_data["auth_url"]

    @patch("google_auth_oauthlib.flow.Flow")
    def test_google_calendar_auth_fails_with_invalid_config(self, mock_flow_class):
        """Test that Google Calendar auth returns error with invalid config."""
        # Create a config without Google Calendar
        mock_config = Mock()
        mock_config.providers.calendar.kind = "ics"
        mock_config.providers.calendar.ics_url = "https://example.com/calendar.ics"
        self.app.config["CONFIG"] = mock_config

        # Make the request
        response = self.client.get("/api/oauth/google")

        # Assert the response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "error" in response_data
