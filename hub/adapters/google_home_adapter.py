"""Adapter for Google Home devices using Google Cast as a transport."""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from ..models import CastingDevice
from .google_cast_adapter import GoogleCastAdapter, discover_google_cast_devices


class GoogleHomeAdapter:
    """Adapter for Google Home devices (using Google Assistant SDK or similar)"""

    def __init__(self, device_config: Dict[str, Any]):
        """
        Initialize the Google Home adapter

        Args:
            device_config: Configuration for the Google Home device
        """
        self.config = device_config
        self.name = device_config.get("name", "Google Home Device")
        self.host = device_config.get("host")
        self.device_id = device_config.get("device_id")
        self.access_token = device_config.get("access_token")
        self.tts_url_template = device_config.get("tts_url_template")
        self.tts_content_type = device_config.get("tts_content_type", "audio/mpeg")
        self.media_content_type = device_config.get("media_content_type", "audio/mp3")
        self._connected = False
        self._cast_adapter: Optional[GoogleCastAdapter] = None
        self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        """Connect to the Google Home device via Google Cast."""
        try:
            self._cast_adapter = GoogleCastAdapter(
                {
                    "name": self.name,
                    "host": self.host,
                    "port": self.config.get("port", 8009),
                }
            )
            self._connected = self._cast_adapter.connect()
            if self._connected:
                self.logger.info("Connected to Google Home device: %s", self.name)
            return self._connected
        except Exception as e:
            self.logger.error("Failed to connect to Google Home device %s: %s", self.name, e)
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from the Google Home device"""
        if self._cast_adapter:
            self._cast_adapter.disconnect()
            self._cast_adapter = None
        self._connected = False
        self.logger.info(f"Disconnected from Google Home device: {self.name}")

    def send_text_command(self, text: str) -> bool:
        """Send a text command via TTS."""
        return self.speak_text(text)

    def play_media(self, media_url: str, title: str = "", description: str = "") -> bool:
        """Play media on the Google Home device"""
        if not self._connected and not self.connect():
            self.logger.error("Google Home device %s is not connected", self.name)
            return False

        try:
            if not self._cast_adapter:
                self.logger.error("Google Cast adapter is not available for %s", self.name)
                return False
            return self._cast_adapter.play_media(
                media_url,
                content_type=self.media_content_type,
                title=title,
                thumb="",
            )
        except Exception as e:
            self.logger.error("Failed to play media on %s: %s", self.name, e)
            return False

    def speak_text(self, text: str) -> bool:
        """Make the Google Home device speak text using a TTS URL template."""
        if not text:
            self.logger.error("No text provided for Google Home TTS")
            return False
        if not self._connected and not self.connect():
            self.logger.error("Google Home device %s is not connected", self.name)
            return False
        if not self.tts_url_template:
            self.logger.error("TTS URL template is not configured for %s", self.name)
            return False

        tts_url = self.tts_url_template.format(text=quote_plus(text))
        try:
            if not self._cast_adapter:
                self.logger.error("Google Cast adapter is not available for %s", self.name)
                return False
            return self._cast_adapter.play_media(
                tts_url,
                content_type=self.tts_content_type,
                title="TTS",
                thumb="",
            )
        except Exception as e:
            self.logger.error("Failed to make %s speak: %s", self.name, e)
            return False

    def speak(self, text: str) -> bool:
        """Compatibility method for IoTService commands."""
        return self.speak_text(text)

    def get_device_info(self) -> Dict[str, Any]:
        """Get device information"""
        if self._cast_adapter:
            info = self._cast_adapter.get_device_info()
        else:
            info = {}
        info.update(
            {
                "name": self.name,
                "device_type": "google_home",
                "host": self.host,
                "device_id": self.device_id,
            }
        )
        return info

    def is_connected(self) -> bool:
        """Check if adapter is connected to device"""
        if self._cast_adapter:
            return self._cast_adapter.is_connected()
        return self._connected


def discover_google_home_devices() -> List[CastingDevice]:
    """Discover Google Home devices using Google Cast discovery."""
    try:
        devices = []
        cast_devices = discover_google_cast_devices()
        for device in cast_devices:
            name = (device.friendly_name or device.name or "").lower()
            if "home" in name or "nest" in name:
                devices.append(
                    CastingDevice(
                        name=device.name,
                        device_id=device.device_id,
                        device_type="google_home",
                        ip_address=device.ip_address,
                        port=device.port,
                        friendly_name=device.friendly_name,
                    )
                )
        return devices
    except Exception as e:
        logging.error(f"Failed to discover Google Home devices: {e}")
        return []
