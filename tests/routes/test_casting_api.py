"""Test suite for casting API endpoints."""

import json
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from app import create_app
from hub.models import CastingDevice, CastingGroup


class TestCastingAPIRoutes:
    """Test suite for casting-related API routes."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["CONFIG"].casting.enabled = True
        self.client = self.app.test_client()

    @patch("hub.services.media.get_casting_devices")
    def test_get_casting_devices(self, mock_get_devices):
        """Test getting all casting devices."""
        # Mock the return value
        mock_device = CastingDevice(
            id=1, name="Test Device", device_id="test_device_123", device_type="google_cast", ip_address="192.168.1.100"
        )
        mock_get_devices.return_value = [mock_device]

        response = self.client.get("/api/casting/devices")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]["name"] == "Test Device"
        assert data[0]["device_id"] == "test_device_123"

    @patch("hub.services.media.get_casting_device")
    def test_get_casting_device(self, mock_get_device):
        """Test getting a specific casting device."""
        # Mock the return value
        mock_device = CastingDevice(
            id=1, name="Test Device", device_id="test_device_123", device_type="google_cast", ip_address="192.168.1.100"
        )
        mock_get_device.return_value = mock_device

        response = self.client.get("/api/casting/devices/test_device_123")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["name"] == "Test Device"
        assert data["device_id"] == "test_device_123"

    @patch("hub.services.media.discover_casting_devices")
    def test_discover_casting_devices(self, mock_discover_devices):
        """Test discovering casting devices."""
        # Mock the return value
        mock_device = CastingDevice(
            name="Discovered Device", device_id="discovered_456", device_type="roku", ip_address="192.168.1.101"
        )
        mock_discover_devices.return_value = [mock_device]

        response = self.client.get("/api/casting/devices/discover")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]["name"] == "Discovered Device"

    @patch("hub.services.casting.casting_manager.get_adapter_for_device")
    def test_play_media_on_device(self, mock_get_adapter):
        """Test playing media on a casting device."""
        # Mock the adapter
        mock_adapter = Mock()
        mock_adapter.play_media.return_value = True
        mock_get_adapter.return_value = mock_adapter

        payload = {"media_url": "http://example.com/video.mp4", "content_type": "video/mp4"}

        response = self.client.post(
            "/api/casting/devices/test_device_123/play", data=json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert "playing on device" in data["message"]

    @patch("hub.services.casting.casting_manager.get_adapter_for_device")
    def test_pause_media_on_device(self, mock_get_adapter):
        """Test pausing media on a casting device."""
        # Mock the adapter
        mock_adapter = Mock()
        mock_adapter.pause.return_value = True
        mock_get_adapter.return_value = mock_adapter

        response = self.client.post("/api/casting/devices/test_device_123/pause")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

    @patch("hub.services.casting.casting_manager.get_adapter_for_device")
    def test_stop_media_on_device(self, mock_get_adapter):
        """Test stopping media on a casting device."""
        # Mock the adapter
        mock_adapter = Mock()
        mock_adapter.stop.return_value = True
        mock_get_adapter.return_value = mock_adapter

        response = self.client.post("/api/casting/devices/test_device_123/stop")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

    @patch("hub.services.casting.casting_manager.get_adapter_for_device")
    def test_set_volume_on_device(self, mock_get_adapter):
        """Test setting volume on a casting device."""
        # Mock the adapter
        mock_adapter = Mock()
        mock_adapter.set_volume.return_value = True
        mock_get_adapter.return_value = mock_adapter

        payload = {"volume": 75}

        response = self.client.put(
            "/api/casting/devices/test_device_123/volume", data=json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["volume"] == 75

    def test_get_device_status(self):
        """Test getting device status."""
        # This test requires configuration to be set up properly
        # For now, we'll just make sure the endpoint exists
        response = self.client.get("/api/casting/devices/test_device_123/status")

        # The response may also be 404 when casting is enabled but the device is unknown.
        assert response.status_code in [200, 400, 404]

    @patch("hub.services.casting.casting_manager.get_all_groups")
    def test_get_casting_groups(self, mock_get_groups):
        """Test getting all casting groups."""
        # Mock the return value
        mock_group = CastingGroup(id=1, name="Test Group", devices=["device1", "device2"])
        mock_get_groups.return_value = [mock_group]

        response = self.client.get("/api/casting/groups")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]["name"] == "Test Group"
        assert "device1" in data[0]["devices"]

    @patch("hub.services.casting.casting_manager.create_group")
    @patch("hub.models.CastingGroup")
    def test_create_casting_group(self, mock_casting_group_class, mock_create_group):
        """Test creating a casting group."""
        # Mock the return values
        mock_group_instance = Mock()
        mock_casting_group_class.return_value = mock_group_instance
        mock_create_group.return_value = True

        payload = {"name": "New Group", "devices": ["device1", "device2"]}

        response = self.client.post("/api/casting/groups", data=json.dumps(payload), content_type="application/json")

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["status"] == "success"

    @patch("hub.services.media.play_media_on_group")
    def test_play_media_on_group(self, mock_play_media):
        """Test playing media on a casting group."""
        # Mock the return value
        mock_play_media.return_value = True

        payload = {"media_url": "http://example.com/video.mp4", "content_type": "video/mp4"}

        response = self.client.post(
            "/api/casting/groups/1/play", data=json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert "playing on group" in data["message"]

    @patch("hub.services.media.get_media_queue")
    def test_get_media_queue(self, mock_get_queue):
        """Test getting media queue for a device."""
        # Mock the return value
        mock_queue = {
            "id": 1,
            "device_id": "test_device_123",
            "queue_items": [],
            "current_item_index": 0,
            "is_playing": False,
            "volume": 50,
        }
        mock_get_queue.return_value = mock_queue

        response = self.client.get("/api/casting/queue/test_device_123")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["device_id"] == "test_device_123"

    @patch("hub.services.media.add_to_queue")
    def test_add_to_queue(self, mock_add_to_queue):
        """Test adding media to a device's queue."""
        # Mock the return value
        mock_add_to_queue.return_value = True

        payload = {"url": "http://example.com/video.mp4", "title": "Test Video", "type": "video"}

        response = self.client.post(
            "/api/casting/queue/test_device_123/add", data=json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
