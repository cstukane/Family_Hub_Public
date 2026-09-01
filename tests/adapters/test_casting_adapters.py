"""Test suite for casting adapters."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from hub.adapters.alexa_adapter import AlexaAdapter
from hub.adapters.google_cast_adapter import (
    PYCHROMECAST_AVAILABLE,
    GoogleCastAdapter,
    discover_google_cast_devices,
)
from hub.adapters.roku_adapter import ROKU_AVAILABLE, RokuAdapter
from hub.models import CastingDevice


class TestGoogleCastAdapter:
    """Test suite for GoogleCastAdapter."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        if not PYCHROMECAST_AVAILABLE:
            pytest.skip("pychromecast not available")
        self.config = {"name": "Test Chromecast", "host": "192.168.1.100", "port": 8009}
        self.adapter = GoogleCastAdapter(self.config)

    @patch("hub.adapters.google_cast_adapter.pychromecast")
    def test_connect(self, mock_pychromecast):
        """Test connecting to a Google Cast device."""
        mock_chromecast = Mock()
        mock_chromecast.wait = Mock()
        mock_chromecast.media_controller = Mock()
        mock_pychromecast.Chromecast.return_value = mock_chromecast

        result = self.adapter.connect()

        assert result is True
        assert self.adapter._chromecast is not None
        assert self.adapter._media_controller is not None

    @patch("hub.adapters.google_cast_adapter.pychromecast")
    def test_play_media(self, mock_pychromecast):
        """Test playing media on a Google Cast device."""
        mock_chromecast = Mock()
        mock_chromecast.wait = Mock()
        mock_chromecast.media_controller = Mock()
        mock_chromecast.media_controller.block_until_active = Mock()
        mock_pychromecast.Chromecast.return_value = mock_chromecast

        self.adapter.connect()

        result = self.adapter.play_media("http://example.com/video.mp4")

        assert result is True
        mock_chromecast.media_controller.play_media.assert_called_once()

    @patch("hub.adapters.google_cast_adapter.pychromecast")
    def test_pause_media(self, mock_pychromecast):
        """Test pausing media on a Google Cast device."""
        mock_chromecast = Mock()
        mock_chromecast.wait = Mock()
        mock_chromecast.media_controller = Mock()
        mock_pychromecast.Chromecast.return_value = mock_chromecast

        self.adapter.connect()

        result = self.adapter.pause()

        assert result is True
        mock_chromecast.media_controller.pause.assert_called_once()

    @patch("hub.adapters.google_cast_adapter.pychromecast")
    def test_stop_media(self, mock_pychromecast):
        """Test stopping media on a Google Cast device."""
        mock_chromecast = Mock()
        mock_chromecast.wait = Mock()
        mock_chromecast.media_controller = Mock()
        mock_pychromecast.Chromecast.return_value = mock_chromecast

        self.adapter.connect()

        result = self.adapter.stop()

        assert result is True
        mock_chromecast.media_controller.stop.assert_called_once()

    @patch("hub.adapters.google_cast_adapter.pychromecast")
    def test_set_volume(self, mock_pychromecast):
        """Test setting volume on a Google Cast device."""
        mock_chromecast = Mock()
        mock_chromecast.wait = Mock()
        mock_chromecast.set_volume = Mock()
        mock_pychromecast.Chromecast.return_value = mock_chromecast

        self.adapter.connect()

        result = self.adapter.set_volume(0.5)

        assert result is True
        mock_chromecast.set_volume.assert_called_once_with(0.5)

    @patch("hub.adapters.google_cast_adapter.pychromecast")
    def test_get_volume(self, mock_pychromecast):
        """Test getting volume from a Google Cast device."""
        mock_chromecast = Mock()
        mock_chromecast.wait = Mock()
        mock_chromecast.status = Mock()
        mock_chromecast.status.volume_level = 0.7
        mock_pychromecast.Chromecast.return_value = mock_chromecast

        self.adapter.connect()

        volume = self.adapter.get_volume()

        assert volume == 0.7


class TestRokuAdapter:
    """Test suite for RokuAdapter."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        if not ROKU_AVAILABLE:
            pytest.skip("roku not available")
        self.config = {"name": "Test Roku", "host": "192.168.1.101", "port": 8060}
        self.adapter = RokuAdapter(self.config)

    @patch("hub.adapters.roku_adapter.Roku")
    def test_connect(self, mock_roku_class):
        """Test connecting to a Roku device."""
        mock_roku_instance = Mock()
        mock_roku_class.return_value = mock_roku_instance

        result = self.adapter.connect()

        assert result is True
        assert self.adapter._roku is not None
        mock_roku_class.assert_called_once_with("192.168.1.101", port=8060)

    @patch("hub.adapters.roku_adapter.Roku")
    def test_launch_app(self, mock_roku_class):
        """Test launching an app on a Roku device."""
        mock_roku_instance = Mock()
        mock_app = Mock()
        mock_roku_instance.__getitem__ = Mock(return_value=mock_app)
        mock_app.launch = Mock()
        mock_roku_class.return_value = mock_roku_instance

        self.adapter.connect()

        result = self.adapter.launch_app("youtube")

        assert result is True
        mock_roku_instance.__getitem__.assert_called_once_with("youtube")
        mock_app.launch.assert_called_once()

    @patch("hub.adapters.roku_adapter.Roku")
    def test_send_key_press(self, mock_roku_class):
        """Test sending a key press to a Roku device."""
        mock_roku_instance = Mock()
        mock_roku_instance.home = Mock()
        mock_roku_class.return_value = mock_roku_instance

        self.adapter.connect()

        result = self.adapter.send_key_press("home")

        assert result is True
        mock_roku_instance.home.assert_called_once()


class TestAlexaAdapter:
    """Test suite for AlexaAdapter."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.config = {
            "name": "Test Alexa",
            "access_token": "test_token",
            "device_serial_number": "test_serial",
            "command_url": "http://alexa.local/command",
        }
        self.adapter = AlexaAdapter(self.config)

    def test_connect(self):
        """Test connecting to an Alexa device."""
        result = self.adapter.connect()

        assert result is True
        assert "Bearer test_token" in self.adapter._session.headers.get("Authorization")

    def test_play_media(self):
        """Test playing media on an Alexa device."""
        with patch.object(self.adapter._session, "post") as mock_post:
            mock_post.return_value.status_code = 200
            result = self.adapter.play_media("http://example.com/audio.mp3")

            assert result is True
            mock_post.assert_called_once()

    def test_speak(self):
        """Test speaking text on an Alexa device."""
        with patch.object(self.adapter._session, "post") as mock_post:
            mock_post.return_value.status_code = 200
            result = self.adapter.speak("Hello World")

            assert result is True
            mock_post.assert_called_once()


@patch("hub.adapters.google_cast_adapter.pychromecast")
def test_discover_google_cast_devices(mock_pychromecast):
    """Test discovering Google Cast devices."""
    if not PYCHROMECAST_AVAILABLE:
        pytest.skip("pychromecast not available")
    # Mock the discovery response
    mock_service = Mock()
    mock_service.device = Mock()
    mock_service.device.friendly_name = "Test Chromecast"
    mock_service.uuid = "test-uuid"
    mock_service.host = "192.168.1.100"
    mock_service.port = 8009

    mock_pychromecast.get_chromecasts.return_value = ([mock_service], Mock())

    devices = discover_google_cast_devices()

    assert len(devices) == 1
    assert devices[0].name == "Test Chromecast"
    assert devices[0].device_id == "test-uuid"
    assert devices[0].ip_address == "192.168.1.100"
