"""Tests for the Home Assistant adapter."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from hub.adapters.homeassistant import HomeAssistantAdapter, initialize_ha_adapter


class TestHomeAssistantAdapter:
    """Test cases for the Home Assistant adapter."""

    def test_initialize_ha_adapter_returns_none_if_invalid_config(self):
        """Test that initialize_ha_adapter returns None when config is invalid."""
        # Test with no config
        result = initialize_ha_adapter(None)
        assert result is None

        # Test with missing base_url
        result = initialize_ha_adapter({"access_token": "token"})
        assert result is None

        # Test with missing access_token
        result = initialize_ha_adapter({"base_url": "http://localhost:8123"})
        assert result is None

        # Test with valid config
        result = initialize_ha_adapter({"base_url": "http://localhost:8123", "access_token": "test_token"})
        assert isinstance(result, HomeAssistantAdapter)

    @patch("hub.adapters.homeassistant.set_cache")
    @patch("hub.adapters.homeassistant.get_cache")
    @patch("hub.adapters.homeassistant.rate_limited_get")
    def test_get_entity_state_success(self, mock_get, mock_get_cache, mock_set_cache):
        """Test that get_entity_state works correctly."""
        # Mock cache to return None to bypass cache check
        mock_get_cache.return_value = None
        # Mock set_cache to do nothing
        mock_set_cache.return_value = None

        # Mock the response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity_id": "light.test_light",
            "state": "on",
            "attributes": {"brightness": 200},
        }
        mock_get.return_value = mock_response

        adapter = HomeAssistantAdapter("http://localhost:8123", "test_token")
        result = adapter.get_entity_state("light.test_light")

        assert result is not None
        assert result["entity_id"] == "light.test_light"
        assert result["state"] == "on"
        assert result["attributes"]["brightness"] == 200

        # Verify the request was made correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "http://localhost:8123/api/states/light.test_light"
        assert kwargs["headers"]["Authorization"] == "Bearer test_token"
        assert kwargs["service_name"] == "homeassistant"

    @patch("hub.adapters.homeassistant.set_cache")
    @patch("hub.adapters.homeassistant.get_cache")
    @patch("hub.adapters.homeassistant.rate_limited_get")
    def test_get_entity_state_returns_none_on_error(self, mock_get, mock_get_cache, mock_set_cache):
        """Test that get_entity_state returns None on error."""
        # Mock cache to return None to bypass cache check
        mock_get_cache.return_value = None
        # Mock set_cache to do nothing
        mock_set_cache.return_value = None

        # Mock an error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        adapter = HomeAssistantAdapter("http://localhost:8123", "test_token")
        result = adapter.get_entity_state("light.nonexistent")

        assert result is None

    @patch("hub.adapters.homeassistant.set_cache")
    @patch("hub.adapters.homeassistant.get_cache")
    @patch("hub.adapters.homeassistant.rate_limited_get")
    def test_get_entities_success(self, mock_get, mock_get_cache, mock_set_cache):
        """Test that get_entities works correctly."""
        # Mock cache to return None to bypass cache check
        mock_get_cache.return_value = None
        # Mock set_cache to do nothing
        mock_set_cache.return_value = None

        # Mock the response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"entity_id": "light.test_light", "state": "on"},
            {"entity_id": "switch.test_switch", "state": "off"},
        ]
        mock_get.return_value = mock_response

        adapter = HomeAssistantAdapter("http://localhost:8123", "test_token")
        result = adapter.get_entities()

        assert len(result) == 2
        assert result[0]["entity_id"] == "light.test_light"
        assert result[1]["entity_id"] == "switch.test_switch"

    @patch("hub.adapters.homeassistant.set_cache")
    @patch("hub.adapters.homeassistant.get_cache")
    @patch("hub.adapters.homeassistant.rate_limited_get")
    def test_get_entities_with_domain_filter(self, mock_get, mock_get_cache, mock_set_cache):
        """Test that get_entities filters by domain correctly."""
        # Mock cache to return None to bypass cache check
        mock_get_cache.return_value = None
        # Mock set_cache to do nothing
        mock_set_cache.return_value = None

        # Mock the response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"entity_id": "light.test_light", "state": "on"},
            {"entity_id": "switch.test_switch", "state": "off"},
            {"entity_id": "light.another_light", "state": "off"},
        ]
        mock_get.return_value = mock_response

        adapter = HomeAssistantAdapter("http://localhost:8123", "test_token")
        result = adapter.get_entities(domain="light")

        assert len(result) == 2
        for entity in result:
            assert entity["entity_id"].startswith("light.")

    @patch("hub.adapters.homeassistant.rate_limited_post")
    def test_call_service_success(self, mock_post):
        """Test that call_service works correctly."""
        # Mock the response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        adapter = HomeAssistantAdapter("http://localhost:8123", "test_token")
        result = adapter.call_service("light", "turn_on", {"entity_id": "light.test_light"})

        assert result is True

        # Verify the request was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:8123/api/services/light/turn_on"
        assert kwargs["json"]["entity_id"] == "light.test_light"

    @patch("hub.adapters.homeassistant.rate_limited_post")
    def test_call_service_returns_false_on_error(self, mock_post):
        """Test that call_service returns False on error."""
        # Mock an error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        adapter = HomeAssistantAdapter("http://localhost:8123", "test_token")
        result = adapter.call_service("light", "turn_on", {"entity_id": "light.test_light"})

        assert result is False

    def test_adapter_initialization(self):
        """Test that the adapter initializes correctly."""
        adapter = HomeAssistantAdapter("http://localhost:8123", "test_token")

        assert adapter.base_url == "http://localhost:8123"
        assert adapter.access_token == "test_token"
        assert adapter.headers["Authorization"] == "Bearer test_token"
        assert adapter.headers["Content-Type"] == "application/json"

    @patch("hub.adapters.homeassistant.set_cache")
    @patch("hub.adapters.homeassistant.get_cache")
    @patch("hub.adapters.homeassistant.rate_limited_get")
    def test_get_area_entities(self, mock_get, mock_get_cache, mock_set_cache):
        """Test that get_area_entities works correctly."""
        # Mock cache to return None to bypass cache check
        mock_get_cache.return_value = None
        # Mock set_cache to do nothing
        mock_set_cache.return_value = None

        # Mock the responses
        mock_states_response = Mock()
        mock_states_response.status_code = 200
        mock_states_response.json.return_value = [
            {"entity_id": "light.living_room_light", "attributes": {"area_id": "living_room"}},
            {"entity_id": "switch.kitchen_switch", "attributes": {"area_id": "kitchen"}},
        ]

        mock_areas_response = Mock()
        mock_areas_response.status_code = 200
        mock_areas_response.json.return_value = [
            {"area_id": "living_room", "name": "Living Room"},
            {"area_id": "kitchen", "name": "Kitchen"},
        ]

        # Mock two different calls to requests.get
        def side_effect(url, *args, **kwargs):
            if "states" in url:
                return mock_states_response
            elif "areas" in url:
                return mock_areas_response

        mock_get.side_effect = side_effect

        adapter = HomeAssistantAdapter("http://localhost:8123", "test_token")
        result = adapter.get_area_entities("living_room")

        assert len(result) == 1
        assert result[0]["entity_id"] == "light.living_room_light"
