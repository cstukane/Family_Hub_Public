"""Test suite for casting service functionality."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from hub.models import CastingDevice, CastingGroup, MediaQueue
from hub.services.casting import CastingDeviceManager


class TestCastingDeviceManager:
    """Test suite for CastingDeviceManager service."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.manager = CastingDeviceManager()

    @patch("hub.services.casting.get_db")
    def test_get_device_by_id(self, mock_get_db):
        """Test getting a casting device by ID."""

        # Mock the database response with a Row-like object
        class MockRow(list):
            def __init__(self, data):
                super().__init__(data)
                self._data = data

        mock_row_data = [
            1,  # id
            "Test Device",  # name
            "test_device_123",  # device_id
            "google_cast",  # device_type
            "192.168.1.100",  # ip_address
            8009,  # port
            "Test Chromecast",  # friendly_name
            1,  # is_active
            datetime.now(),  # last_seen
        ]

        mock_row = MockRow(mock_row_data)

        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_cursor
        mock_get_db.return_value = mock_db

        device = self.manager.get_device_by_id("test_device_123")

        assert device is not None
        assert device.name == "Test Device"
        assert device.device_id == "test_device_123"
        assert device.device_type == "google_cast"

    @patch("hub.services.casting.get_db")
    def test_get_device_by_id_not_found(self, mock_get_db):
        """Test getting a casting device that doesn't exist."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_db.execute.return_value = mock_cursor
        mock_get_db.return_value = mock_db

        device = self.manager.get_device_by_id("nonexistent")

        assert device is None

    @patch("hub.services.casting.get_db")
    def test_create_device(self, mock_get_db):
        """Test creating a new casting device."""
        mock_db = Mock()
        mock_db.execute.return_value = None
        mock_db.commit.return_value = None
        mock_get_db.return_value = mock_db

        device = CastingDevice(
            name="New Test Device", device_id="new_device_456", device_type="roku", ip_address="192.168.1.101"
        )

        result = self.manager.create_device(device)

        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("hub.services.casting.get_db")
    def test_update_device(self, mock_get_db):
        """Test updating an existing casting device."""
        mock_db = Mock()
        mock_db.execute.return_value = None
        mock_db.commit.return_value = None
        mock_get_db.return_value = mock_db

        device = CastingDevice(
            name="Updated Test Device", device_id="update_device_789", device_type="alexa", is_active=True
        )

        result = self.manager.update_device(device)

        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("hub.services.casting.get_db")
    def test_delete_device(self, mock_get_db):
        """Test deleting a casting device."""
        mock_db = Mock()
        mock_db.execute.return_value = None
        mock_db.commit.return_value = None
        mock_get_db.return_value = mock_db

        result = self.manager.delete_device("test_device_123")

        assert result is True
        assert mock_db.execute.call_count == 2  # Two DELETE statements
        mock_db.commit.assert_called_once()

    @patch("hub.services.casting.get_db")
    def test_get_all_devices(self, mock_get_db):
        """Test getting all casting devices."""

        # Mock the database response with Row-like objects
        class MockRow(list):
            def __init__(self, data):
                super().__init__(data)
                self._data = data

        mock_row_data = [
            1,  # id
            "Test Device",  # name
            "test_device_123",  # device_id
            "google_cast",  # device_type
            "192.168.1.100",  # ip_address
            8009,  # port
            "Test Chromecast",  # friendly_name
            1,  # is_active
            datetime.now(),  # last_seen
        ]

        mock_row = MockRow(mock_row_data)

        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [mock_row]
        mock_db.execute.return_value = mock_cursor
        mock_get_db.return_value = mock_db

        devices = self.manager.get_all_devices()

        assert len(devices) == 1
        assert devices[0].name == "Test Device"

    @patch("hub.services.casting.json.loads")
    @patch("hub.services.casting.get_db")
    def test_get_queue_for_device(self, mock_get_db, mock_json_loads):
        """Test getting media queue for a device."""
        mock_json_loads.return_value = [{"url": "http://example.com/media.mp4", "title": "Test Media", "type": "video"}]

        # Mock the database response with Row-like objects
        class MockRow(list):
            def __init__(self, data):
                super().__init__(data)
                self._data = data

        mock_row_data = [
            1,  # id
            "test_device_123",  # device_id
            "[]",  # queue_items JSON
            0,  # current_item_index
            1,  # is_playing
            50,  # volume
        ]

        mock_row = MockRow(mock_row_data)

        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_cursor
        mock_get_db.return_value = mock_db

        queue = self.manager.get_queue_for_device("test_device_123")

        assert queue is not None
        assert queue.device_id == "test_device_123"
        assert queue.volume == 50

    @patch("hub.services.casting.json.dumps")
    @patch("hub.services.casting.get_db")
    def test_update_queue_for_device(self, mock_get_db, mock_json_dumps):
        """Test updating media queue for a device."""
        mock_json_dumps.return_value = "[]"

        mock_db = Mock()
        mock_db.execute.return_value = None
        mock_db.commit.return_value = None
        mock_get_db.return_value = mock_db

        queue = MediaQueue(device_id="test_device_123", volume=75)

        result = self.manager.update_queue_for_device(queue)

        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("hub.services.casting.json.loads")
    @patch("hub.services.casting.get_db")
    def test_get_all_groups(self, mock_get_db, mock_json_loads):
        """Test getting all casting groups."""
        mock_json_loads.return_value = ["device1", "device2"]

        # Mock the database response with Row-like objects
        class MockRow(list):
            def __init__(self, data):
                super().__init__(data)
                self._data = data

        mock_row_data = [1, "Living Room Group", '["device1", "device2"]', 1]  # id  # name  # devices JSON  # is_active

        mock_row = MockRow(mock_row_data)

        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [mock_row]
        mock_db.execute.return_value = mock_cursor
        mock_get_db.return_value = mock_db

        groups = self.manager.get_all_groups()

        assert len(groups) == 1
        assert groups[0].name == "Living Room Group"
        assert "device1" in groups[0].devices

    @patch("hub.services.casting.json.dumps")
    @patch("hub.services.casting.get_db")
    def test_create_group(self, mock_get_db, mock_json_dumps):
        """Test creating a new casting group."""
        mock_json_dumps.return_value = '["device1", "device2"]'

        mock_db = Mock()
        mock_db.execute.return_value = None
        mock_db.commit.return_value = None
        mock_get_db.return_value = mock_db

        group = CastingGroup(name="Test Group", devices=["device1", "device2"])

        result = self.manager.create_group(group)

        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
