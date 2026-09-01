"""
Services for managing plugins in the Family Hub application.
"""

from typing import Any, Dict, List

from hub.db import get_db
from hub.plugins.base import PluginStatus
from hub.plugins.manager import plugin_manager


def get_installed_plugins() -> List[Dict[str, Any]]:
    """Get information about all installed plugins."""
    db = get_db()

    # Get plugins from the database
    plugin_rows = db.execute(
        """SELECT name, version, author, description, type, status, enabled
           FROM plugins ORDER BY name"""
    ).fetchall()

    plugins_info = []
    for row in plugin_rows:
        # Get additional runtime info from the plugin manager if available
        plugin = plugin_manager.get_plugin(row["name"])
        runtime_info = {}
        if plugin:
            runtime_info = plugin.get_metadata()

        plugins_info.append(
            {
                "name": row["name"],
                "version": row["version"],
                "author": row["author"],
                "description": row["description"],
                "type": row["type"],
                "status": row["status"],
                "enabled": bool(row["enabled"]),
                "runtime_info": runtime_info,
            }
        )

    return plugins_info


def get_plugin_settings(plugin_name: str) -> Dict[str, Any]:
    """Get settings for a specific plugin."""
    db = get_db()

    settings_rows = db.execute(
        """SELECT setting_key, setting_value
           FROM plugin_settings
           WHERE plugin_name = ?""",
        (plugin_name,),
    ).fetchall()

    settings = {}
    for row in settings_rows:
        settings[row["setting_key"]] = row["setting_value"]

    return settings


def update_plugin_settings(plugin_name: str, settings: Dict[str, Any]) -> bool:
    """Update settings for a specific plugin."""
    try:
        db = get_db()

        # Remove existing settings for this plugin
        db.execute("DELETE FROM plugin_settings WHERE plugin_name = ?", (plugin_name,))

        # Add new settings
        for key, value in settings.items():
            db.execute(
                """INSERT INTO plugin_settings (plugin_name, setting_key, setting_value)
                   VALUES (?, ?, ?)""",
                (plugin_name, key, str(value)),
            )

        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def log_plugin_event(plugin_name: str, level: str, message: str) -> bool:
    """Log an event for a specific plugin."""
    try:
        db = get_db()

        db.execute(
            """INSERT INTO plugin_logs (plugin_name, level, message)
               VALUES (?, ?, ?)""",
            (plugin_name, level, message),
        )

        db.commit()
        return True
    except Exception:
        return False


def get_plugin_logs(plugin_name: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get logs for a specific plugin."""
    db = get_db()

    log_rows = db.execute(
        """SELECT level, message, timestamp
           FROM plugin_logs
           WHERE plugin_name = ?
           ORDER BY timestamp DESC
           LIMIT ?""",
        (plugin_name, limit),
    ).fetchall()

    logs = []
    for row in log_rows:
        logs.append({"level": row["level"], "message": row["message"], "timestamp": row["timestamp"]})

    return logs


def get_all_plugin_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Get logs for all plugins."""
    db = get_db()

    log_rows = db.execute(
        """SELECT plugin_name, level, message, timestamp
           FROM plugin_logs
           ORDER BY timestamp DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()

    logs = []
    for row in log_rows:
        logs.append(
            {
                "plugin_name": row["plugin_name"],
                "level": row["level"],
                "message": row["message"],
                "timestamp": row["timestamp"],
            }
        )

    return logs


def enable_plugin(plugin_name: str) -> bool:
    """Enable a plugin."""
    try:
        # Update in database
        db = get_db()
        db.execute(
            """UPDATE plugins
               SET status = ?, enabled = 1, updated_at = CURRENT_TIMESTAMP
               WHERE name = ?""",
            (PluginStatus.ENABLED.value, plugin_name),
        )
        db.commit()

        # Update in plugin manager
        return plugin_manager.enable_plugin(plugin_name)
    except Exception:
        return False


def disable_plugin(plugin_name: str) -> bool:
    """Disable a plugin."""
    try:
        # Update in database
        db = get_db()
        db.execute(
            """UPDATE plugins
               SET status = ?, enabled = 0, updated_at = CURRENT_TIMESTAMP
               WHERE name = ?""",
            (PluginStatus.DISABLED.value, plugin_name),
        )
        db.commit()

        # Update in plugin manager
        return plugin_manager.disable_plugin(plugin_name)
    except Exception:
        return False


def install_plugin(plugin_name: str, version: str, author: str, description: str, plugin_type: str) -> bool:
    """Install a plugin (add it to the database)."""
    try:
        db = get_db()

        # Insert or update the plugin record
        db.execute(
            """INSERT OR REPLACE INTO plugins
               (name, version, author, description, type, status, enabled)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (plugin_name, version, author, description, plugin_type, PluginStatus.INSTALLED.value, 0),  # Start disabled
        )

        db.commit()
        return True
    except Exception:
        return False


def uninstall_plugin(plugin_name: str) -> bool:
    """Uninstall a plugin (remove it from the database)."""
    try:
        db = get_db()

        # Remove plugin settings and logs first due to foreign key constraints
        db.execute("DELETE FROM plugin_settings WHERE plugin_name = ?", (plugin_name,))
        db.execute("DELETE FROM plugin_logs WHERE plugin_name = ?", (plugin_name,))

        # Remove plugin record
        db.execute("DELETE FROM plugins WHERE name = ?", (plugin_name,))

        db.commit()
        return True
    except Exception:
        return False


def update_plugin(plugin_name: str, version: str) -> bool:
    """Update a plugin version."""
    try:
        db = get_db()

        db.execute(
            """UPDATE plugins
               SET version = ?, status = ?, updated_at = CURRENT_TIMESTAMP
               WHERE name = ?""",
            (version, PluginStatus.UPDATING.value, plugin_name),
        )

        db.commit()
        return True
    except Exception:
        return False


def get_enabled_plugins_count() -> int:
    """Get the number of enabled plugins."""
    db = get_db()

    count = db.execute(
        """SELECT COUNT(*)
           FROM plugins
           WHERE enabled = 1 AND status = ?""",
        (PluginStatus.ENABLED.value,),
    ).fetchone()[0]

    return count


def get_total_plugins_count() -> int:
    """Get the total number of installed plugins."""
    db = get_db()

    count = db.execute(
        """SELECT COUNT(*)
           FROM plugins"""
    ).fetchone()[0]

    return count


def get_plugin_stats() -> Dict[str, int]:
    """Get statistics about plugins."""
    enabled_count = get_enabled_plugins_count()
    total_count = get_total_plugins_count()

    return {"total": total_count, "enabled": enabled_count, "disabled": total_count - enabled_count}


def get_plugins_by_type(plugin_type: str) -> List[Dict[str, Any]]:
    """Get plugins filtered by type."""
    db = get_db()

    plugin_rows = db.execute(
        """SELECT name, version, author, description, status, enabled
           FROM plugins
           WHERE type = ?
           ORDER BY name""",
        (plugin_type,),
    ).fetchall()

    plugins = []
    for row in plugin_rows:
        plugins.append(
            {
                "name": row["name"],
                "version": row["version"],
                "author": row["author"],
                "description": row["description"],
                "status": row["status"],
                "enabled": bool(row["enabled"]),
            }
        )

    return plugins


def search_plugins(query: str) -> List[Dict[str, Any]]:
    """Search for plugins by name, author, or description."""
    db = get_db()

    plugin_rows = db.execute(
        """SELECT name, version, author, description, type, status, enabled
           FROM plugins
           WHERE name LIKE ? OR author LIKE ? OR description LIKE ?
           ORDER BY name""",
        (f"%{query}%", f"%{query}%", f"%{query}%"),
    ).fetchall()

    plugins = []
    for row in plugin_rows:
        plugins.append(
            {
                "name": row["name"],
                "version": row["version"],
                "author": row["author"],
                "description": row["description"],
                "type": row["type"],
                "status": row["status"],
                "enabled": bool(row["enabled"]),
            }
        )

    return plugins
