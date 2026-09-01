"""Adapter for Alexa devices."""

import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from hub.utils.http import acquire_rate_limit, rate_limited_get

from ..models import CastingDevice


class AlexaAdapter:
    """Adapter for Alexa devices using HTTP command endpoints."""

    def __init__(self, device_config: Dict[str, Any]):
        self.config = device_config
        self.name = device_config.get("name", "Alexa Device")
        self.host = device_config.get("host")
        self.access_token = device_config.get("access_token")
        self.device_serial_number = device_config.get("device_serial_number")
        self.device_type = device_config.get("device_type")
        self.api_base_url = device_config.get("api_base_url", "https://api.amazonalexa.com")
        self.devices_endpoint = device_config.get("devices_endpoint", "/v1/devices")
        self.speak_url = device_config.get("speak_url", device_config.get("command_url"))
        self.play_url = device_config.get("play_url", device_config.get("command_url"))
        self.locale = device_config.get("locale", "en-US")
        self.auth_required = device_config.get("auth_required", True)
        self.timeout = int(device_config.get("timeout", 10))
        self._session = requests.Session()
        self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        """Configure session headers for Alexa requests."""
        if self.auth_required and not self.access_token:
            self.logger.error("Access token not provided for Alexa device: %s", self.name)
            return False

        if self.access_token:
            self._session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        self.logger.info("Alexa adapter ready for device: %s", self.name)
        return True

    def disconnect(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def play_media(self, media_url: str, title: str = "", description: str = "") -> bool:
        """Play media via a configured command endpoint."""
        if not self._ensure_ready(media_url=media_url):
            return False
        command_url = self._resolve_command_url(self.play_url, "play")
        if not command_url:
            return False

        payload = {
            "type": "play_media",
            "device": self._device_payload(),
            "media": {
                "url": media_url,
                "title": title,
                "description": description,
            },
        }
        return self._post_command(command_url, payload, "Alexa play")

    def speak(self, text: str) -> bool:
        """Speak text via a configured command endpoint."""
        if not self._ensure_ready(text=text):
            return False
        command_url = self._resolve_command_url(self.speak_url, "speak")
        if not command_url:
            return False

        payload = {
            "type": "speak",
            "device": self._device_payload(),
            "text": text,
            "locale": self.locale,
        }
        return self._post_command(command_url, payload, "Alexa speak")

    def get_device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "name": self.name,
            "device_type": "alexa",
            "host": self.host,
            "serial_number": self.device_serial_number,
        }

    def is_connected(self) -> bool:
        """Check if adapter has an access token."""
        return self.access_token is not None

    def _device_payload(self) -> Dict[str, Any]:
        payload = {"serial_number": self.device_serial_number}
        if self.device_type:
            payload["device_type"] = self.device_type
        return payload

    def _ensure_ready(self, text: str = "", media_url: str = "") -> bool:
        if self.auth_required and not self.access_token:
            self.logger.error("Access token not provided for Alexa device: %s", self.name)
            return False
        if not self.device_serial_number:
            self.logger.error("Device serial number not provided for %s", self.name)
            return False
        if text == "" and media_url == "":
            return True
        if text and not text.strip():
            self.logger.error("No text provided for Alexa speech on %s", self.name)
            return False
        if media_url and not media_url.strip():
            self.logger.error("No media URL provided for %s", self.name)
            return False
        return True

    def _resolve_command_url(self, command_url: Optional[str], context: str) -> Optional[str]:
        if not command_url:
            self.logger.error("Alexa %s url is not configured for %s", context, self.name)
            return None
        return _resolve_url(self.api_base_url, command_url)

    def _post_command(self, url: str, payload: Dict[str, Any], context: str) -> bool:
        if _should_log_payload():
            self.logger.debug("%s payload: %s", context, _safe_payload(payload))
        if not acquire_rate_limit("alexa"):
            self.logger.error("Alexa command rate limited for %s", self.name)
            return False
        try:
            response = self._session.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            self.logger.error("%s request failed: %s", context, exc)
            return False

        if 200 <= response.status_code < 300:
            return True

        self.logger.error("%s failed: %s %s", context, response.status_code, response.text)
        return False


def discover_alexa_devices() -> List[CastingDevice]:
    """Discover Alexa devices using the Alexa Devices API."""
    try:
        access_token = os.environ.get("ALEXA_ACCESS_TOKEN")
        if not access_token:
            return []

        api_base_url = os.environ.get("ALEXA_API_BASE_URL", "https://api.amazonalexa.com")
        devices_endpoint = os.environ.get("ALEXA_DEVICES_ENDPOINT", "/v1/devices")
        url = _resolve_url(api_base_url, devices_endpoint)

        response = rate_limited_get(
            url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10, service_name="alexa"
        )
        response.raise_for_status()
        payload = response.json()
        devices = []

        for device in payload.get("devices", []):
            name = device.get("friendlyName") or device.get("name") or "Alexa Device"
            serial = device.get("deviceSerialNumber") or device.get("serialNumber") or name
            devices.append(
                CastingDevice(
                    name=name,
                    device_id=serial,
                    device_type="alexa",
                    ip_address=None,
                    port=None,
                    friendly_name=name,
                )
            )

        return devices
    except Exception as e:
        logging.error("Failed to discover Alexa devices: %s", e)
        return []


def _resolve_url(base_url: str, path_or_url: str) -> str:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    return urljoin(base_url.rstrip("/") + "/", path_or_url.lstrip("/"))


def _safe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    scrubbed = dict(payload)
    device = scrubbed.get("device", {})
    if isinstance(device, dict) and "serial_number" in device:
        device = dict(device)
        device["serial_number"] = "***"
        scrubbed["device"] = device
    return scrubbed


def _should_log_payload() -> bool:
    return os.environ.get("ALEXA_LOG_PAYLOADS", "").lower() in {"1", "true", "yes"}
