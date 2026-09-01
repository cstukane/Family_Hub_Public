"""Tests for the new API routes related to Google Calendar and Home Assistant."""

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


class TestHomeAssistantAPIRoutes:
    """Test cases for the Home Assistant API routes."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.client = self.app.test_client()

        # Create a test config with Home Assistant settings
        mock_config = Mock()
        mock_config.providers = Mock()
        mock_config.providers.homeassistant = Mock()
        mock_config.providers.homeassistant.base_url = "http://localhost:8123"
        mock_config.providers.homeassistant.access_token = "test_token"

        # Temporarily override the app config
        self.app.config["CONFIG"] = mock_config

    @patch("hub.routes.api.initialize_ha_adapter")
    def test_get_ha_entities_success(self, mock_init_adapter):
        """Test getting Home Assistant entities successfully."""
        # Mock the HA adapter and its method
        mock_adapter = Mock()
        mock_adapter.get_entities.return_value = [
            {"entity_id": "light.test_light", "state": "on"},
            {"entity_id": "switch.test_switch", "state": "off"},
        ]
        mock_init_adapter.return_value = mock_adapter

        # Make the request
        response = self.client.get("/api/ha/entities")

        # Assert the response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert len(response_data) == 2
        assert response_data[0]["entity_id"] == "light.test_light"

    @patch("hub.routes.api.initialize_ha_adapter")
    def test_get_ha_entities_by_domain(self, mock_init_adapter):
        """Test getting Home Assistant entities by domain successfully."""
        # Mock the HA adapter and its method
        mock_adapter = Mock()
        mock_adapter.get_entities.return_value = [{"entity_id": "light.test_light", "state": "on"}]
        mock_init_adapter.return_value = mock_adapter

        # Make the request with domain query param
        response = self.client.get("/api/ha/entities?domain=light")

        # Assert the response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert len(response_data) == 1
        assert response_data[0]["entity_id"] == "light.test_light"

    @patch("hub.routes.api.initialize_ha_adapter")
    def test_get_ha_entity_success(self, mock_init_adapter):
        """Test getting a specific Home Assistant entity successfully."""
        # Mock the HA adapter and its method
        mock_adapter = Mock()
        mock_adapter.get_entity_state.return_value = {
            "entity_id": "light.test_light",
            "state": "on",
            "attributes": {"brightness": 200},
        }
        mock_init_adapter.return_value = mock_adapter

        # Make the request
        response = self.client.get("/api/ha/entities/light.test_light")

        # Assert the response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data["entity_id"] == "light.test_light"
        assert response_data["state"] == "on"

    @patch("hub.routes.api.initialize_ha_adapter")
    def test_get_ha_entity_not_found(self, mock_init_adapter):
        """Test getting a specific Home Assistant entity returns 404 when not found."""
        # Mock the HA adapter to return None (entity not found)
        mock_adapter = Mock()
        mock_adapter.get_entity_state.return_value = None
        mock_init_adapter.return_value = mock_adapter

        # Make the request
        response = self.client.get("/api/ha/entities/light.nonexistent")

        # Assert the response
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert "error" in response_data

    @patch("hub.routes.api.initialize_ha_adapter")
    def test_call_ha_service_success(self, mock_init_adapter):
        """Test calling a Home Assistant service successfully."""
        # Mock the HA adapter and its method
        mock_adapter = Mock()
        mock_adapter.call_service.return_value = True
        mock_init_adapter.return_value = mock_adapter

        # Prepare test data
        service_data = {"entity_id": "light.test_light"}

        # Make the request
        response = self.client.post(
            "/api/ha/services/light/turn_on", data=json.dumps(service_data), content_type="application/json"
        )

        # Assert the response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data["status"] == "Service call successful"

    @patch("hub.routes.api.initialize_ha_adapter")
    def test_call_ha_service_fails(self, mock_init_adapter):
        """Test calling a Home Assistant service fails when service call returns False."""
        # Mock the HA adapter to return False
        mock_adapter = Mock()
        mock_adapter.call_service.return_value = False
        mock_init_adapter.return_value = mock_adapter

        # Prepare test data
        service_data = {"entity_id": "light.test_light"}

        # Make the request
        response = self.client.post(
            "/api/ha/services/light/turn_on", data=json.dumps(service_data), content_type="application/json"
        )

        # Assert the response
        assert response.status_code == 500
        response_data = json.loads(response.data)
        assert "error" in response_data
