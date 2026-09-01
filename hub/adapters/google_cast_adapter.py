"""Adapter for Google Cast devices (Chromecast, Google Home, etc.)"""

import logging
from typing import Any, Dict, List, Optional

# Try to import pychromecast, but gracefully handle if it's not available
try:
    import pychromecast
    from pychromecast.controllers.media import MediaStatus

    PYCHROMECAST_AVAILABLE = True
except ImportError:
    PYCHROMECAST_AVAILABLE = False
    MediaStatus = None
    pychromecast = None

from ..models import CastingDevice


class GoogleCastAdapter:
    """Adapter for Google Cast devices"""

    def __init__(self, device_config: Dict[str, Any]):
        """
        Initialize the Google Cast adapter

        Args:
            device_config: Configuration for the Google Cast device
        """
        if not PYCHROMECAST_AVAILABLE:
            raise ImportError("pychromecast is not available. Please install it to use Google Cast features.")

        self.config = device_config
        self.name = device_config.get("name", "Google Cast Device")
        self.host = device_config.get("host")
        self.port = device_config.get("port", 8009)
        self._chromecast = None
        self._media_controller = None
        self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        """Connect to the Google Cast device"""
        if not PYCHROMECAST_AVAILABLE:
            self.logger.error("pychromecast is not available")
            return False

        try:
            if self.host:
                # Connect to specific device
                self._chromecast = pychromecast.Chromecast(self.host, port=self.port)
            else:
                # Find device by name
                services, browser = pychromecast.discovery.discover_listed_chromecasts(friendly_names=[self.name])
                if services:
                    self._chromecast = pychromecast.Chromecast(services[0].host, port=services[0].port)

            if self._chromecast:
                # Wait for the device to be ready
                self._chromecast.wait()
                self._media_controller = self._chromecast.media_controller
                self.logger.info(f"Connected to Google Cast device: {self.name}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Google Cast device {self.name}: {e}")
            return False

        return False

    def disconnect(self) -> None:
        """Disconnect from the Google Cast device"""
        if not PYCHROMECAST_AVAILABLE:
            self.logger.error("pychromecast is not available")
            return

        if self._chromecast:
            self._chromecast.disconnect()
            self._chromecast = None
            self._media_controller = None

    def play_media(self, media_url: str, content_type: str = "video/mp4", title: str = "", thumb: str = "") -> bool:
        """Play media on the Google Cast device"""
        if not PYCHROMECAST_AVAILABLE:
            self.logger.error("pychromecast is not available")
            return False

        try:
            if not self._media_controller:
                if not self.connect():
                    return False

            # Load media on the device
            self._media_controller.play_media(media_url, content_type, title=title, thumb=thumb)
            self._media_controller.block_until_active()
            return True
        except Exception as e:
            self.logger.error(f"Failed to play media on {self.name}: {e}")
            return False

    def pause(self) -> bool:
        """Pause media on the Google Cast device"""
        if not PYCHROMECAST_AVAILABLE:
            self.logger.error("pychromecast is not available")
            return False

        try:
            if not self._media_controller:
                if not self.connect():
                    return False

            self._media_controller.pause()
            return True
        except Exception as e:
            self.logger.error(f"Failed to pause media on {self.name}: {e}")
            return False

    def stop(self) -> bool:
        """Stop media on the Google Cast device"""
        if not PYCHROMECAST_AVAILABLE:
            self.logger.error("pychromecast is not available")
            return False

        try:
            if not self._media_controller:
                if not self.connect():
                    return False

            self._media_controller.stop()
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop media on {self.name}: {e}")
            return False

    def play(self) -> bool:
        """Resume media on the Google Cast device"""
        if not PYCHROMECAST_AVAILABLE:
            self.logger.error("pychromecast is not available")
            return False

        try:
            if not self._media_controller:
                if not self.connect():
                    return False

            self._media_controller.play()
            return True
        except Exception as e:
            self.logger.error(f"Failed to play media on {self.name}: {e}")
            return False

    def set_volume(self, volume: float) -> bool:
        """Set volume on the Google Cast device (0.0 to 1.0)"""
        if not PYCHROMECAST_AVAILABLE:
            self.logger.error("pychromecast is not available")
            return False

        try:
            if not self._chromecast:
                if not self.connect():
                    return False

            self._chromecast.set_volume(volume)
            return True
        except Exception as e:
            self.logger.error(f"Failed to set volume on {self.name}: {e}")
            return False

    def get_volume(self) -> Optional[float]:
        """Get current volume from the Google Cast device"""
        if not PYCHROMECAST_AVAILABLE:
            self.logger.error("pychromecast is not available")
            return None

        try:
            if not self._chromecast:
                if not self.connect():
                    return None

            return self._chromecast.status.volume_level
        except Exception as e:
            self.logger.error(f"Failed to get volume from {self.name}: {e}")
            return None

    def get_media_status(self) -> Optional[MediaStatus]:
        """Get current media status from the Google Cast device"""
        if not PYCHROMECAST_AVAILABLE:
            self.logger.error("pychromecast is not available")
            return None

        try:
            if not self._media_controller:
                if not self.connect():
                    return None

            return self._media_controller.status
        except Exception as e:
            self.logger.error(f"Failed to get media status from {self.name}: {e}")
            return None

    def get_device_info(self) -> Dict[str, Any]:
        """Get device information"""
        if not PYCHROMECAST_AVAILABLE:
            self.logger.error("pychromecast is not available")
            return {}

        try:
            if not self._chromecast:
                if not self.connect():
                    return {}

            info = {
                "friendly_name": self._chromecast.device.friendly_name,
                "manufacturer": self._chromecast.device.manufacturer,
                "model_name": self._chromecast.device.model_name,
                "uuid": str(self._chromecast.uuid),
                "host": self._chromecast.host,
                "port": self._chromecast.port,
            }
            return info
        except Exception as e:
            self.logger.error(f"Failed to get device info from {self.name}: {e}")
            return {}

    def is_connected(self) -> bool:
        """Check if adapter is connected to device"""
        if not PYCHROMECAST_AVAILABLE:
            return False
        return self._chromecast is not None and self._chromecast.status is not None


def discover_google_cast_devices() -> List[CastingDevice]:
    """Discover Google Cast devices on the network"""
    if not PYCHROMECAST_AVAILABLE:
        logging.error("pychromecast is not available")
        return []

    try:
        devices = []
        services, browser = pychromecast.get_chromecasts()

        for service in services:
            device_info = {
                "name": service.device.friendly_name,
                "device_id": str(service.uuid),
                "device_type": "google_cast",
                "ip_address": service.host,
                "port": service.port,
                "friendly_name": service.device.friendly_name,
            }

            casting_device = CastingDevice(
                name=device_info["name"],
                device_id=device_info["device_id"],
                device_type=device_info["device_type"],
                ip_address=device_info["ip_address"],
                port=device_info["port"],
                friendly_name=device_info["friendly_name"],
            )
            devices.append(casting_device)

        # Stop the browser
        browser.stop_discovery()

        return devices
    except Exception as e:
        logging.error(f"Failed to discover Google Cast devices: {e}")
        return []
