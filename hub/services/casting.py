"""Service for casting device management and multi-room audio"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import List, Optional

from flask import current_app

# Import adapters with optional fallbacks
try:
    from ..adapters import AlexaAdapter, GoogleCastAdapter, RokuAdapter
except ImportError as e:
    # Define placeholders that will raise errors if used
    _casting_import_err = str(e)

    def AlexaAdapter(*args, **kwargs):
        raise ImportError(f"Alexa adapter not available: {_casting_import_err}")

    def GoogleCastAdapter(*args, **kwargs):
        raise ImportError(f"Google Cast adapter not available: {_casting_import_err}")

    def RokuAdapter(*args, **kwargs):
        raise ImportError(f"Roku adapter not available: {_casting_import_err}")


from ..db import get_db
from ..models import CastingDevice, CastingGroup, MediaQueue


class CastingDeviceManager:
    """Service for managing casting devices and multi-room audio"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.adapters = {}

    def register_adapter(self, device_id: str, adapter) -> bool:
        """Register an adapter for a device"""
        try:
            self.adapters[device_id] = adapter
            return True
        except Exception as e:
            self.logger.error(f"Failed to register adapter for device {device_id}: {e}")
            return False

    def get_device_by_id(self, device_id: str) -> Optional[CastingDevice]:
        """Get a casting device by ID from the database"""
        try:
            db = get_db()
            cur = db.execute(
                """SELECT id, name, device_id, device_type, ip_address, port, friendly_name,
                          is_active, last_seen
                   FROM casting_devices
                   WHERE device_id = ?""",
                (device_id,),
            )
            row = cur.fetchone()

            if row:
                return CastingDevice(
                    id=row[0],
                    name=row[1],
                    device_id=row[2],
                    device_type=row[3],
                    ip_address=row[4],
                    port=row[5],
                    friendly_name=row[6],
                    is_active=bool(row[7]),
                    last_seen=row[8],
                )
            return None
        except Exception as e:
            self.logger.error(f"Failed to get device by ID {device_id}: {e}")
            return None

    def get_all_devices(self) -> List[CastingDevice]:
        """Get all casting devices from the database"""
        try:
            db = get_db()
            cur = db.execute(
                """SELECT id, name, device_id, device_type, ip_address, port, friendly_name,
                          is_active, last_seen
                   FROM casting_devices
                   ORDER BY name"""
            )
            rows = cur.fetchall()

            devices = []
            for row in rows:
                device = CastingDevice(
                    id=row[0],
                    name=row[1],
                    device_id=row[2],
                    device_type=row[3],
                    ip_address=row[4],
                    port=row[5],
                    friendly_name=row[6],
                    is_active=bool(row[7]),
                    last_seen=row[8],
                )
                devices.append(device)
            return devices
        except Exception as e:
            self.logger.error(f"Failed to get all devices: {e}")
            return []

    def create_device(self, device: CastingDevice) -> bool:
        """Create a new casting device in the database"""
        try:
            db = get_db()
            db.execute(
                """INSERT INTO casting_devices
                   (name, device_id, device_type, ip_address, port, friendly_name)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    device.name,
                    device.device_id,
                    device.device_type,
                    device.ip_address,
                    device.port,
                    device.friendly_name,
                ),
            )
            db.commit()
            return True
        except sqlite3.IntegrityError:
            # Device ID already exists
            self.logger.warning(f"Device with ID {device.device_id} already exists")
            return False
        except Exception as e:
            self.logger.error(f"Failed to create device {device.name}: {e}")
            return False

    def update_device(self, device: CastingDevice) -> bool:
        """Update an existing casting device in the database"""
        try:
            db = get_db()
            db.execute(
                """UPDATE casting_devices
                   SET name = ?, device_type = ?, ip_address = ?, port = ?,
                       friendly_name = ?, is_active = ?
                   WHERE device_id = ?""",
                (
                    device.name,
                    device.device_type,
                    device.ip_address,
                    device.port,
                    device.friendly_name,
                    int(device.is_active),
                    device.device_id,
                ),
            )
            db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to update device {device.name}: {e}")
            return False

    def delete_device(self, device_id: str) -> bool:
        """Delete a casting device from the database"""
        try:
            db = get_db()
            db.execute("DELETE FROM casting_devices WHERE device_id = ?", (device_id,))
            db.execute("DELETE FROM media_queues WHERE device_id = ?", (device_id,))
            db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete device {device_id}: {e}")
            return False

    def get_queue_for_device(self, device_id: str) -> Optional[MediaQueue]:
        """Get the media queue for a specific device"""
        try:
            db = get_db()
            cur = db.execute(
                """SELECT id, device_id, queue_items, current_item_index, is_playing, volume
                   FROM media_queues
                   WHERE device_id = ?""",
                (device_id,),
            )
            row = cur.fetchone()

            if row:
                queue_items = json.loads(row[2]) if row[2] else []
                return MediaQueue(
                    id=row[0],
                    device_id=row[1],
                    queue_items=queue_items,
                    current_item_index=row[3],
                    is_playing=bool(row[4]),
                    volume=row[5],
                )
            return None
        except Exception as e:
            self.logger.error(f"Failed to get queue for device {device_id}: {e}")
            return None

    def create_queue_for_device(self, device_id: str) -> bool:
        """Create a media queue for a device if it doesn't exist"""
        try:
            db = get_db()
            # Check if queue already exists
            cur = db.execute("SELECT id FROM media_queues WHERE device_id = ?", (device_id,))
            if cur.fetchone():
                return True  # Queue already exists

            # Create new queue
            db.execute(
                """INSERT INTO media_queues (device_id, queue_items, volume)
                   VALUES (?, ?, ?)""",
                (device_id, json.dumps([]), 50),
            )
            db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to create queue for device {device_id}: {e}")
            return False

    def update_queue_for_device(self, queue: MediaQueue) -> bool:
        """Update the media queue for a device"""
        try:
            import json

            db = get_db()
            db.execute(
                """UPDATE media_queues
                   SET queue_items = ?, current_item_index = ?, is_playing = ?, volume = ?
                   WHERE device_id = ?""",
                (
                    json.dumps(queue.queue_items),
                    queue.current_item_index,
                    int(queue.is_playing),
                    queue.volume,
                    queue.device_id,
                ),
            )
            db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to update queue for device {queue.device_id}: {e}")
            return False

    def get_all_groups(self) -> List[CastingGroup]:
        """Get all casting groups from the database"""
        try:
            db = get_db()
            cur = db.execute(
                """SELECT id, name, devices, is_active
                   FROM casting_groups
                   ORDER BY name"""
            )
            rows = cur.fetchall()

            groups = []
            for row in rows:
                devices = json.loads(row[2]) if row[2] else []
                group = CastingGroup(id=row[0], name=row[1], devices=devices, is_active=bool(row[3]))
                groups.append(group)
            return groups
        except Exception as e:
            self.logger.error(f"Failed to get all groups: {e}")
            return []

    def create_group(self, group: CastingGroup) -> bool:
        """Create a new casting group in the database"""
        try:
            db = get_db()
            db.execute(
                """INSERT INTO casting_groups
                   (name, devices, is_active)
                   VALUES (?, ?, ?)""",
                (group.name, json.dumps(group.devices), int(group.is_active)),
            )
            db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to create group {group.name}: {e}")
            return False

    def delete_group(self, group_id: int) -> bool:
        """Delete a casting group from the database"""
        try:
            db = get_db()
            db.execute("DELETE FROM casting_groups WHERE id = ?", (group_id,))
            db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete group {group_id}: {e}")
            return False

    def get_adapter_for_device(self, device_id: str):
        """Get the appropriate adapter for a device"""
        # Get device info from DB to determine type
        device = self.get_device_by_id(device_id)
        if not device:
            return None

        # Get config from app
        config = current_app.config.get("CONFIG")
        if not config or not hasattr(config, "casting") or not config.casting.devices:
            return None

        # Find device config
        device_config = None
        for dev_config in config.casting.devices:
            if dev_config.id == device_id:
                device_config = dev_config
                break

        if not device_config:
            return None

        # Create adapter based on device type
        if device.device_type == "google_cast":
            adapter = GoogleCastAdapter(device_config.model_dump())
            if adapter.connect():
                return adapter
        elif device.device_type == "roku":
            adapter = RokuAdapter(device_config.model_dump())
            if adapter.connect():
                return adapter
        elif device.device_type == "alexa":
            adapter = AlexaAdapter(device_config.model_dump())
            if adapter.connect():
                return adapter

        return None

    def discover_devices(self) -> List[CastingDevice]:
        """Discover available casting devices on the network"""
        # Import discovery functions with error handling
        try:
            from ..adapters import discover_alexa_devices, discover_google_cast_devices, discover_roku_devices
        except ImportError as e:
            self.logger.error(f"Error importing discovery functions: {e}")
            return []

        discovered_devices = []

        # Discover Google Cast devices
        try:
            google_cast_devices = discover_google_cast_devices()
            discovered_devices.extend(google_cast_devices)
        except Exception as e:
            self.logger.error(f"Error discovering Google Cast devices: {e}")

        # Discover Roku devices
        try:
            roku_devices = discover_roku_devices()
            discovered_devices.extend(roku_devices)
        except Exception as e:
            self.logger.error(f"Error discovering Roku devices: {e}")

        # Discover Alexa devices
        try:
            alexa_devices = discover_alexa_devices()
            discovered_devices.extend(alexa_devices)
        except Exception as e:
            self.logger.error(f"Error discovering Alexa devices: {e}")

        return discovered_devices

    def refresh_device_list(self) -> bool:
        """Refresh the list of discovered devices in the database"""
        try:
            discovered_devices = self.discover_devices()

            # Get currently stored devices
            current_devices = self.get_all_devices()
            current_device_ids = {device.device_id for device in current_devices}
            discovered_device_ids = {device.device_id for device in discovered_devices}

            # Add new devices
            for device in discovered_devices:
                if device.device_id not in current_device_ids:
                    device.last_seen = datetime.now()
                    self.create_device(device)
                else:
                    # Update last seen timestamp for existing devices
                    db = get_db()
                    db.execute(
                        """UPDATE casting_devices SET last_seen = ? WHERE device_id = ?""",
                        (datetime.now(), device.device_id),
                    )
                    db.commit()

            # Mark devices as inactive if they haven't been seen recently
            for device in current_devices:
                if device.device_id not in discovered_device_ids:
                    # Update device to mark as inactive if it hasn't been seen in 5 minutes
                    if device.last_seen:
                        current_time = datetime.now()
                        time_diff = current_time - device.last_seen
                        if time_diff.total_seconds() > 300:  # 5 minutes
                            db = get_db()
                            db.execute(
                                """UPDATE casting_devices SET is_active = 0 WHERE device_id = ?""", (device.device_id,)
                            )
                            db.commit()

            return True
        except Exception as e:
            self.logger.error(f"Failed to refresh device list: {e}")
            return False


# Global instance
casting_manager = CastingDeviceManager()
