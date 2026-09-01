"""Adapter for Roku devices"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# Try to import roku, but gracefully handle if it's not available
try:
    from roku import Roku

    ROKU_AVAILABLE = True
except ImportError:
    ROKU_AVAILABLE = False
    Roku = None

from ..models import CastingDevice


class RokuAdapter:
    """Adapter for Roku devices"""

    def __init__(self, device_config: Dict[str, Any]):
        """
        Initialize the Roku adapter

        Args:
            device_config: Configuration for the Roku device
        """
        if not ROKU_AVAILABLE:
            raise ImportError("roku is not available. Please install it to use Roku features.")

        self.config = device_config
        self.name = device_config.get("name", "Roku Device")
        self.host = device_config.get("host")
        self.port = device_config.get("port", 8060)
        self._roku = None
        self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        """Connect to the Roku device"""
        if not ROKU_AVAILABLE:
            self.logger.error("roku is not available")
            return False

        try:
            if self.host:
                self._roku = Roku(self.host, port=self.port)
                self.logger.info(f"Connected to Roku device: {self.name} at {self.host}")
                return True
            else:
                self.logger.error(f"Host not specified for Roku device: {self.name}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to connect to Roku device {self.name}: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the Roku device"""
        if not ROKU_AVAILABLE:
            self.logger.error("roku is not available")
            return

        self._roku = None

    def launch_app(self, app_id: str) -> bool:
        """Launch an app on the Roku device"""
        if not ROKU_AVAILABLE:
            self.logger.error("roku is not available")
            return False

        try:
            if not self._roku:
                if not self.connect():
                    return False

            # Find and launch the app
            app = self._roku[app_id]
            if app:
                app.launch()
                return True
            else:
                self.logger.warning(f"App {app_id} not found on Roku device {self.name}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to launch app {app_id} on {self.name}: {e}")
            return False

    def play_media(self, media_url: str) -> bool:
        """Play media on the Roku device (requires specific app support)"""
        if not ROKU_AVAILABLE:
            self.logger.error("roku is not available")
            return False

        try:
            if not self._roku:
                if not self.connect():
                    return False

            # This is a simplified implementation
            # In reality, you might need to launch specific streaming apps
            # and then send remote commands to play specific content
            self.logger.warning("Roku media playback requires app-specific integration")
            return True
        except Exception as e:
            self.logger.error(f"Failed to play media on {self.name}: {e}")
            return False

    def send_key_press(self, key: str) -> bool:
        """Send a key press command to the Roku device"""
        if not ROKU_AVAILABLE:
            self.logger.error("roku is not available")
            return False

        try:
            if not self._roku:
                if not self.connect():
                    return False

            if hasattr(self._roku, key):
                getattr(self._roku, key)()
                return True
            else:
                self.logger.warning(f"Key {key} not found on Roku device {self.name}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to send key press {key} on {self.name}: {e}")
            return False

    def get_current_app(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently running app"""
        if not ROKU_AVAILABLE:
            self.logger.error("roku is not available")
            return None

        try:
            if not self._roku:
                if not self.connect():
                    return None

            active_app = self._roku.active_app
            if active_app:
                return {"app_id": active_app.id, "app_name": active_app.name, "is_roku_app": active_app.is_roku_app}
            return None
        except Exception as e:
            self.logger.error(f"Failed to get current app from {self.name}: {e}")
            return None

    def get_installed_apps(self) -> List[Dict[str, Any]]:
        """Get list of installed apps"""
        if not ROKU_AVAILABLE:
            self.logger.error("roku is not available")
            return []

        try:
            if not self._roku:
                if not self.connect():
                    return []

            apps = self._roku.apps
            app_list = []
            for app in apps:
                app_list.append(
                    {"id": app.id, "name": app.name, "version": app.version if hasattr(app, "version") else None}
                )
            return app_list
        except Exception as e:
            self.logger.error(f"Failed to get installed apps from {self.name}: {e}")
            return []

    def get_device_info(self) -> Dict[str, Any]:
        """Get device information"""
        if not ROKU_AVAILABLE:
            self.logger.error("roku is not available")
            return {}

        try:
            if not self._roku:
                if not self.connect():
                    return {}

            device_info = self._roku.device_info
            return {
                "name": device_info.name if hasattr(device_info, "name") else self.name,
                "model": device_info.model if hasattr(device_info, "model") else "Unknown",
                "version": device_info.version if hasattr(device_info, "version") else "Unknown",
                "mac": device_info.mac if hasattr(device_info, "mac") else "Unknown",
                "host": self.host,
                "port": self.port,
            }
        except Exception as e:
            self.logger.error(f"Failed to get device info from {self.name}: {e}")
            return {}

    def is_connected(self) -> bool:
        """Check if adapter is connected to device"""
        if not ROKU_AVAILABLE:
            return False
        return self._roku is not None


def discover_roku_devices() -> List[CastingDevice]:
    """Discover Roku devices on the network"""
    if not ROKU_AVAILABLE:
        logging.getLogger(__name__).error("roku is not available")
        return []

    logger = logging.getLogger(__name__)
    devices: List[CastingDevice] = []
    seen_ids = set()

    try:
        discovered_devices = Roku.discover(timeout=5)
    except Exception as exc:
        logger.error(f"Failed to perform Roku SSDP discovery: {exc}")
        return devices

    def _should_suppress_device_info_error(error: Exception) -> bool:
        message = str(error).lower()
        return "hue personal wireless lighting" in message

    for roku_device in discovered_devices:
        try:
            device_info = roku_device.device_info
        except Exception as exc:
            if _should_suppress_device_info_error(exc):
                logger.info(
                    "Skipping non-Roku SSDP device at %s:%s",
                    roku_device.host,
                    roku_device.port,
                )
            else:
                logger.warning(
                    "Skipping Roku device at %s:%s due to error retrieving device info: %s",
                    roku_device.host,
                    roku_device.port,
                    exc,
                )
            continue

        device_id = getattr(device_info, "sernum", None) or f"roku-{roku_device.host}"
        if device_id in seen_ids:
            continue

        seen_ids.add(device_id)
        friendly_name = getattr(device_info, "userdevicename", None) or getattr(device_info, "modelname", "Roku Device")

        devices.append(
            CastingDevice(
                name=friendly_name,
                device_id=device_id,
                device_type="roku",
                ip_address=roku_device.host,
                port=roku_device.port,
                friendly_name=friendly_name,
                is_active=True,
                last_seen=datetime.now(),
            )
        )

    return devices
