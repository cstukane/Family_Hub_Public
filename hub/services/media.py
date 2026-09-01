import logging
from typing import Any, Dict, List, Optional

from flask import current_app

from ..models import CastingDevice, MediaQueue
from .casting import casting_manager


def resolve_app_action(app_id: str) -> Dict[str, Any]:
    """
    Resolve an app ID to its action configuration.

    Args:
        app_id: The ID of the app to launch

    Returns:
        Dictionary with action details
    """
    # Get the app configuration from the main config
    config = current_app.config.get("CONFIG")
    if not config or not hasattr(config, "apps"):
        return {"error": "Configuration not available", "mode": "error", "url": None, "target": None}

    # Find the app in the configuration
    app_config = None
    for app in config.apps:
        if app.id == app_id:
            app_config = app
            break

    if not app_config:
        return {"error": f"App {app_id} not found in configuration", "mode": "error", "url": None, "target": None}

    # Return the appropriate action based on the app's configuration
    action = {
        "id": app_config.id,
        "label": app_config.label,
        "action": app_config.action,
        "url": getattr(app_config, "url", None),
        "target": getattr(app_config, "target", None),
    }

    return action


def launch_app(app_id: str) -> Dict[str, Any]:
    """
    Execute the launch action for an app.

    Args:
        app_id: The ID of the app to launch

    Returns:
        Dictionary with launch results
    """
    action = resolve_app_action(app_id)

    if "error" in action:
        return action

    # For now, just return the action configuration
    # In a real implementation, this might trigger different types of actions
    # (open iframe, open tab, switch view, run command)
    return {"status": "launched", "app_id": app_id, "action": action}


def get_casting_devices() -> List[CastingDevice]:
    """
    Get all available casting devices.

    Returns:
        List of casting devices
    """
    try:
        return casting_manager.get_all_devices()
    except Exception as e:
        logging.error(f"Error getting casting devices: {e}")
        return []


def get_casting_device(device_id: str) -> Optional[CastingDevice]:
    """
    Get a specific casting device by ID.

    Args:
        device_id: The ID of the device to get

    Returns:
        The casting device or None if not found
    """
    try:
        return casting_manager.get_device_by_id(device_id)
    except Exception as e:
        logging.error(f"Error getting casting device {device_id}: {e}")
        return None


def play_media_on_device(device_id: str, media_url: str, content_type: str = "video/mp4") -> bool:
    """
    Play media on a specific casting device.

    Args:
        device_id: The ID of the device to play on
        media_url: URL of the media to play
        content_type: Content type of the media (default: video/mp4)

    Returns:
        True if successful, False otherwise
    """
    try:
        adapter = casting_manager.get_adapter_for_device(device_id)
        if not adapter:
            logging.error(f"No adapter found for device {device_id}")
            return False

        success = adapter.play_media(media_url, content_type)
        return success
    except Exception as e:
        logging.error(f"Error playing media on device {device_id}: {e}")
        return False


def play_media_on_group(group_id: int, media_url: str, content_type: str = "video/mp4") -> bool:
    """
    Play media on all devices in a group (for multi-room audio).

    Args:
        group_id: The ID of the group to play on
        media_url: URL of the media to play
        content_type: Content type of the media (default: video/mp4)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the group
        groups = casting_manager.get_all_groups()
        target_group = None
        for group in groups:
            if group.id == group_id:
                target_group = group
                break

        if not target_group:
            logging.error(f"Group {group_id} not found")
            return False

        # Play media on each device in the group
        success_count = 0
        for device_id in target_group.devices:
            if play_media_on_device(device_id, media_url, content_type):
                success_count += 1

        return success_count > 0
    except Exception as e:
        logging.error(f"Error playing media on group {group_id}: {e}")
        return False


def get_media_queue(device_id: str) -> Optional[MediaQueue]:
    """
    Get the media queue for a specific device.

    Args:
        device_id: The ID of the device

    Returns:
        MediaQueue object or None if not found
    """
    try:
        return casting_manager.get_queue_for_device(device_id)
    except Exception as e:
        logging.error(f"Error getting media queue for device {device_id}: {e}")
        return None


def add_to_queue(device_id: str, media_item: Dict[str, Any]) -> bool:
    """
    Add a media item to the device's queue.

    Args:
        device_id: The ID of the device
        media_item: Media item to add to the queue

    Returns:
        True if successful, False otherwise
    """
    try:
        queue = casting_manager.get_queue_for_device(device_id)
        if not queue:
            # Create queue if it doesn't exist
            if not casting_manager.create_queue_for_device(device_id):
                return False
            queue = casting_manager.get_queue_for_device(device_id)

        if queue:
            queue.queue_items.append(media_item)
            return casting_manager.update_queue_for_device(queue)
        return False
    except Exception as e:
        logging.error(f"Error adding to queue for device {device_id}: {e}")
        return False


def discover_casting_devices() -> List[CastingDevice]:
    """
    Discover casting devices on the network.

    Returns:
        List of discovered casting devices
    """
    try:
        return casting_manager.discover_devices()
    except Exception as e:
        logging.error(f"Error discovering casting devices: {e}")
        return []
