# Services package initialization

import importlib

from . import (
    admin,
    backup,
    calendar,
    cooking,
    local_voice,
    media,
    notes,
    shopping,
    sports,
    sports_ticker_service,
    timers,
    update,
    voice,
    weather,
    weather_alert,
    webhook,
)

# Import specific functions to make them accessible at the package level
from .admin import (
    authenticate_admin,
    get_config_for_admin,
    get_system_info,
    hash_password,
    is_admin_authenticated,
    logout_admin,
    run_diagnostics,
    update_config_from_admin,
    verify_password,
)
from .backup import (
    create_backup,
    delete_backup,
    get_backup_info,
    list_backups,
    restore_backup,
)
from .calendar import add_event, add_google_calendar_event, get_calendar_status, get_upcoming_events, list_events
from .chore_service import Chore, ChoreService, chore_service
from .cooking import (
    add_ingredients_to_shopping_list,
    create_recipe,
    get_all_recipes,
    get_recipe,
    toggle_ingredient_check,
)
from .local_voice import get_local_processor, init_local_processor
from .media import (
    add_to_queue,
    discover_casting_devices,
    get_casting_device,
    get_casting_devices,
    get_media_queue,
    launch_app,
    play_media_on_device,
    play_media_on_group,
)
from .notes import create_note, delete_note, get_note, list_notes, update_note
from .shopping import (
    create_shopping_item,
    delete_shopping_item,
    get_shopping_item,
    list_shopping_items,
    toggle_shopping_item_done,
    update_shopping_item,
)
from .sports import get_available_leagues, get_sports_data, get_team_info, refresh_sports_data, update_favorite_teams
from .sports_ticker_service import get_sports_ticker_data, refresh_sports_ticker_data
from .timers import (
    check_expired_timers,
    create_timer,
    deactivate_expired_timers,
    delete_timer,
    get_timer,
    list_active_timers,
    update_timer,
)
from .update import (
    check_for_updates,
    get_update_history,
    perform_update,
    rollback_update,
)
from .voice import get_available_commands, process_voice_command
from .weather import get_weather_data

_LAZY_ATTRS = {
    # Casting
    "casting_manager": ("hub.services.casting", "casting_manager"),
    # IoT service
    "iot_service": ("hub.services.iot_service", None),
    "IoTDevice": ("hub.services.iot_service", "IoTDevice"),
    "IoTService": ("hub.services.iot_service", "IoTService"),
    # Music service
    "music": ("hub.services.music", None),
    "music_service": ("hub.services.music", "music_service"),
    "music_controller": ("hub.services.music", "music_controller"),
    # Photo service
    "photos": ("hub.services.photos", None),
    "photo_service": ("hub.services.photos", "photo_service"),
    # Plugin service exports
    "plugins": ("hub.services.plugins", None),
    "disable_plugin": ("hub.services.plugins", "disable_plugin"),
    "enable_plugin": ("hub.services.plugins", "enable_plugin"),
    "get_all_plugin_logs": ("hub.services.plugins", "get_all_plugin_logs"),
    "get_enabled_plugins_count": ("hub.services.plugins", "get_enabled_plugins_count"),
    "get_installed_plugins": ("hub.services.plugins", "get_installed_plugins"),
    "get_plugin_logs": ("hub.services.plugins", "get_plugin_logs"),
    "get_plugin_settings": ("hub.services.plugins", "get_plugin_settings"),
    "get_plugin_stats": ("hub.services.plugins", "get_plugin_stats"),
    "get_plugins_by_type": ("hub.services.plugins", "get_plugins_by_type"),
    "get_total_plugins_count": ("hub.services.plugins", "get_total_plugins_count"),
    "install_plugin": ("hub.services.plugins", "install_plugin"),
    "log_plugin_event": ("hub.services.plugins", "log_plugin_event"),
    "search_plugins": ("hub.services.plugins", "search_plugins"),
    "uninstall_plugin": ("hub.services.plugins", "uninstall_plugin"),
    "update_plugin": ("hub.services.plugins", "update_plugin"),
    "update_plugin_settings": ("hub.services.plugins", "update_plugin_settings"),
}


def __getattr__(name):
    if name in _LAZY_ATTRS:
        module_path, attr_name = _LAZY_ATTRS[name]
        module = importlib.import_module(module_path)
        value = module if attr_name is None else getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'hub.services' has no attribute '{name}'")


from .weather_alert import (
    check_weather_alerts,
    get_active_weather_alerts,
    get_current_weather_data,
    get_weather_alert_history,
    is_weather_severe,
    process_weather_alerts,
)
from .webhook import (
    create_webhook,
    delete_webhook,
    get_all_webhook_logs,
    get_all_webhooks,
    get_webhook,
    get_webhook_logs,
    log_webhook_execution,
    test_webhook_connection,
    trigger_webhook,
    trigger_webhooks_for_event,
    update_webhook,
)

__all__ = [
    "admin",
    "backup",
    "calendar",
    "chore_service",
    "cooking",
    "iot_service",
    "local_voice",
    "media",
    "notes",
    "photos",
    "plugins",
    "shopping",
    "sports",
    "sports_ticker_service",
    "timers",
    "update",
    "voice",
    "weather",
    "webhook",
    "weather_alert",
    "music",
    # Admin functions
    "authenticate_admin",
    "get_config_for_admin",
    "get_system_info",
    "hash_password",
    "is_admin_authenticated",
    "logout_admin",
    "run_diagnostics",
    "update_config_from_admin",
    "verify_password",
    # Backup functions
    "create_backup",
    "delete_backup",
    "get_backup_info",
    "list_backups",
    "restore_backup",
    # Calendar functions
    "list_events",
    "add_event",
    "add_google_calendar_event",
    "get_upcoming_events",
    "get_calendar_status",
    # Chore functions
    "Chore",
    "chore_service",
    "ChoreService",
    # Cooking functions
    "get_recipe",
    "get_all_recipes",
    "create_recipe",
    "add_ingredients_to_shopping_list",
    "toggle_ingredient_check",
    # IoT functions
    "IoTDevice",
    "iot_service",
    "IoTService",
    # Local Voice functions
    "init_local_processor",
    "get_local_processor",
    # Media functions
    "launch_app",
    "get_casting_devices",
    "get_casting_device",
    "play_media_on_device",
    "play_media_on_group",
    "get_media_queue",
    "add_to_queue",
    "discover_casting_devices",
    # Notes functions
    "create_note",
    "delete_note",
    "get_note",
    "list_notes",
    "update_note",
    # Photo functions
    "photo_service",
    # Plugin functions
    "disable_plugin",
    "enable_plugin",
    "get_all_plugin_logs",
    "get_enabled_plugins_count",
    "get_installed_plugins",
    "get_plugin_logs",
    "get_plugin_settings",
    "get_plugins_by_type",
    "get_plugin_stats",
    "get_total_plugins_count",
    "install_plugin",
    "log_plugin_event",
    "search_plugins",
    "uninstall_plugin",
    "update_plugin",
    "update_plugin_settings",
    # Shopping functions
    "create_shopping_item",
    "delete_shopping_item",
    "get_shopping_item",
    "list_shopping_items",
    "toggle_shopping_item_done",
    "update_shopping_item",
    # Update functions
    "check_for_updates",
    "get_update_history",
    "perform_update",
    "rollback_update",
    # Sports functions
    "get_sports_data",
    "get_team_info",
    "get_available_leagues",
    "refresh_sports_data",
    # Sports ticker functions
    "get_sports_ticker_data",
    "refresh_sports_ticker_data",
    # Timer functions
    "create_timer",
    "delete_timer",
    "get_timer",
    "list_active_timers",
    "update_timer",
    "check_expired_timers",
    "deactivate_expired_timers",
    # Voice functions
    "process_voice_command",
    "get_available_commands",
    # Weather functions
    "get_weather_data",
    # Webhook functions
    "create_webhook",
    "delete_webhook",
    "get_all_webhook_logs",
    "get_all_webhooks",
    "get_webhook",
    "get_webhook_logs",
    "log_webhook_execution",
    "test_webhook_connection",
    "trigger_webhook",
    "trigger_webhooks_for_event",
    "update_webhook",
    # Weather alert functions
    "check_weather_alerts",
    "get_active_weather_alerts",
    "get_current_weather_data",
    "get_weather_alert_history",
    "is_weather_severe",
    "process_weather_alerts",
    # Casting functions
    "casting_manager",
    "add_to_queue",
    "discover_casting_devices",
    "get_casting_device",
    "get_casting_devices",
    "get_media_queue",
    "play_media_on_device",
    "play_media_on_group",
    # Music functions
    "music_service",
    "music_controller",
]


def __dir__():
    return sorted(set(__all__ + list(_LAZY_ATTRS.keys())))