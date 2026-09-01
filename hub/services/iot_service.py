"""Service for managing IoT devices and integrations"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from hub.adapters.alexa_adapter import AlexaAdapter
from hub.adapters.google_cast_adapter import GoogleCastAdapter
from hub.adapters.google_home_adapter import GoogleHomeAdapter
from hub.db import get_db


class IoTDevice:
    """Represents an IoT device with all its properties."""

    def __init__(
        self,
        id=None,
        name="",
        device_type="",
        device_id="",
        host=None,
        port=None,
        is_active=True,
        created_at=None,
        updated_at=None,
        config=None,
    ):
        self.id = id
        self.name = name
        self.device_type = device_type  # alexa, google_home, cast, etc.
        self.device_id = device_id
        self.host = host
        self.port = port
        self.is_active = is_active
        self.created_at = created_at
        self.updated_at = updated_at
        self.config = config or {}

    def to_dict(self):
        """Convert IoT device to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "device_type": self.device_type,
            "device_id": self.device_id,
            "host": self.host,
            "port": self.port,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "config": self.config,
        }


_IOT_DISCOVERY_EXECUTOR = ThreadPoolExecutor(max_workers=2)


class IoTService:
    """Service class for managing IoT devices and integrations."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.adapters = {}
        self.devices = {}

    def register_adapter(self, device_type: str, adapter_class):
        """Register an adapter class for a device type."""
        self.adapters[device_type] = adapter_class

    def get_device_adapter(self, device_type: str, device_config: Dict[str, Any]):
        """Get an adapter instance for a specific device type."""
        if device_type not in self.adapters:
            self.logger.error(f"No adapter registered for device type: {device_type}")
            return None

        try:
            adapter_class = self.adapters[device_type]
            return adapter_class(device_config)
        except Exception as e:
            self.logger.error(f"Error creating adapter for {device_type}: {e}")
            return None

    def add_device(
        self,
        name: str,
        device_type: str,
        device_id: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        config: Optional[Dict] = None,
    ) -> Optional[IoTDevice]:
        """Add a new IoT device to the system."""
        try:
            db = get_db()

            query = """
                INSERT INTO iot_devices (name, device_type, device_id, host, port, is_active, config)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            import json

            config_json = json.dumps(config or {})

            result = db.execute(query, (name, device_type, device_id, host, port, True, config_json))
            db.commit()

            # Return the created device
            return self.get_device(result.lastrowid)
        except Exception as e:
            self.logger.error(f"Error adding IoT device: {e}")
            return None

    def get_device(self, device_id: int) -> Optional[IoTDevice]:
        """Get a specific IoT device by ID."""
        try:
            db = get_db()

            query = """
                SELECT id, name, device_type, device_id, host, port, is_active, created_at, updated_at, config
                FROM iot_devices
                WHERE id = ?
            """

            row = db.execute(query, (device_id,)).fetchone()
            if not row:
                return None

            import json

            config = json.loads(row["config"]) if row["config"] else {}

            return IoTDevice(
                id=row["id"],
                name=row["name"],
                device_type=row["device_type"],
                device_id=row["device_id"],
                host=row["host"],
                port=row["port"],
                is_active=bool(row["is_active"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                config=config,
            )
        except Exception as e:
            self.logger.error(f"Error fetching IoT device {device_id}: {e}")
            return None

    def get_devices_by_type(self, device_type: str) -> List[IoTDevice]:
        """Get all IoT devices of a specific type."""
        try:
            db = get_db()

            query = """
                SELECT id, name, device_type, device_id, host, port, is_active, created_at, updated_at, config
                FROM iot_devices
                WHERE device_type = ? AND is_active = 1
            """

            rows = db.execute(query, (device_type,)).fetchall()

            devices = []
            for row in rows:
                import json

                config = json.loads(row["config"]) if row["config"] else {}

                device = IoTDevice(
                    id=row["id"],
                    name=row["name"],
                    device_type=row["device_type"],
                    device_id=row["device_id"],
                    host=row["host"],
                    port=row["port"],
                    is_active=bool(row["is_active"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    config=config,
                )
                devices.append(device)

            return devices
        except Exception as e:
            self.logger.error(f"Error fetching IoT devices of type {device_type}: {e}")
            return []

    def get_all_devices(self) -> List[IoTDevice]:
        """Get all IoT devices."""
        try:
            db = get_db()

            query = """
                SELECT id, name, device_type, device_id, host, port, is_active, created_at, updated_at, config
                FROM iot_devices
                ORDER BY device_type, name
            """

            rows = db.execute(query).fetchall()

            devices = []
            for row in rows:
                import json

                config = json.loads(row["config"]) if row["config"] else {}

                device = IoTDevice(
                    id=row["id"],
                    name=row["name"],
                    device_type=row["device_type"],
                    device_id=row["device_id"],
                    host=row["host"],
                    port=row["port"],
                    is_active=bool(row["is_active"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    config=config,
                )
                devices.append(device)

            return devices
        except Exception as e:
            self.logger.error(f"Error fetching all IoT devices: {e}")
            return []

    def update_device(
        self,
        device_id: int,
        name: Optional[str] = None,
        device_type: Optional[str] = None,
        device_id_new: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        is_active: Optional[bool] = None,
        config: Optional[Dict] = None,
    ) -> Optional[IoTDevice]:
        """Update an existing IoT device."""
        try:
            db = get_db()

            # First get the current device to check if it exists
            current_device = self.get_device(device_id)
            if not current_device:
                return None

            # Prepare update query and parameters
            update_fields = []
            params = []

            if name is not None:
                update_fields.append("name = ?")
                params.append(name)

            if device_type is not None:
                update_fields.append("device_type = ?")
                params.append(device_type)

            if device_id_new is not None:
                update_fields.append("device_id = ?")
                params.append(device_id_new)

            if host is not None:
                update_fields.append("host = ?")
                params.append(host)

            if port is not None:
                update_fields.append("port = ?")
                params.append(port)

            if is_active is not None:
                update_fields.append("is_active = ?")
                params.append(int(is_active))

            if config is not None:
                import json

                update_fields.append("config = ?")
                params.append(json.dumps(config))

            # Always update the updated_at timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")

            if not update_fields:
                return current_device  # No changes to make

            query = f"UPDATE iot_devices SET {', '.join(update_fields)} WHERE id = ?"  # nosec B608
            params.append(device_id)

            db.execute(query, params)
            db.commit()

            # Return the updated device
            return self.get_device(device_id)
        except Exception as e:
            self.logger.error(f"Error updating IoT device {device_id}: {e}")
            return None

    def remove_device(self, device_id: int) -> bool:
        """Remove an IoT device from the system."""
        try:
            db = get_db()

            query = "DELETE FROM iot_devices WHERE id = ?"
            result = db.execute(query, (device_id,))
            db.commit()

            return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error removing IoT device {device_id}: {e}")
            return False

    def send_command_to_device(self, device_id: int, command: str, params: Optional[Dict] = None) -> bool:
        """Send a command to a specific IoT device."""
        try:
            device = self.get_device(device_id)
            if not device:
                self.logger.error(f"Device with ID {device_id} not found")
                return False

            # Get the appropriate adapter for this device type
            adapter = self.get_device_adapter(device.device_type, device.config)
            if not adapter:
                self.logger.error(f"No adapter available for device type {device.device_type}")
                return False

            # Connect to the device
            if not adapter.connect():
                self.logger.error(f"Failed to connect to device {device.name}")
                return False

            # Execute the command based on the command type
            success = False
            if command == "speak":
                text = (params or {}).get("text", "")
                success = adapter.speak(text)
            elif command == "play_media":
                media_url = (params or {}).get("url", "")
                title = (params or {}).get("title", "")
                success = adapter.play_media(media_url, title)
            else:
                self.logger.warning(f"Unknown command: {command}")
                success = False

            adapter.disconnect()
            return success
        except Exception as e:
            self.logger.error(f"Error sending command to device {device_id}: {e}")
            return False

    def discover_devices(self) -> List[IoTDevice]:
        """Discover IoT devices on the network."""
        discovered_devices = []

        # For Alexa devices
        try:
            from hub.adapters.alexa_adapter import discover_alexa_devices

            alexa_devices = discover_alexa_devices()
            discovered_devices.extend(alexa_devices)
        except ImportError:
            self.logger.warning("Alexa adapter not available for device discovery")
        except Exception as e:
            self.logger.error(f"Error discovering Alexa devices: {e}")

        # For Google Cast devices
        try:
            from hub.services.media import discover_casting_devices

            cast_devices = discover_casting_devices()
            # Convert casting devices to IoT devices format
            for cast_device in cast_devices:
                iot_device = IoTDevice(
                    name=cast_device.name,
                    device_type="google_cast",
                    device_id=cast_device.device_id,
                    host=cast_device.ip_address,
                    port=cast_device.port,
                    is_active=cast_device.is_active,
                )
                discovered_devices.append(iot_device)
        except Exception as e:
            self.logger.error(f"Error discovering Google Cast devices: {e}")

        return discovered_devices

    def request_background_discovery(self) -> bool:
        """Trigger device discovery without blocking the caller."""
        try:
            _IOT_DISCOVERY_EXECUTOR.submit(self.discover_devices)
            return True
        except Exception as e:
            self.logger.error(f"Failed to schedule IoT discovery: {e}")
            return False


# Register default adapters
iot_service = IoTService()
iot_service.register_adapter("alexa", AlexaAdapter)
iot_service.register_adapter("google_cast", GoogleCastAdapter)
iot_service.register_adapter("google_home", GoogleHomeAdapter)
