import os
from datetime import datetime

from flask import current_app, jsonify, render_template, request

from hub.integrations import spotify_auth
from hub.plugins.manager import plugin_manager
from hub.plugins.marketplace import PluginMarketplace
from hub.services import casting_manager, media
from hub.services.music_providers.providers import registry as music_provider_registry
from hub.services.music_providers.providers.base import MusicProviderError
from hub.utils.config_helpers import get_config_dict
from hub.utils.decorators import require_admin_rate_limit, require_default_rate_limit, require_ip_whitelist

from . import api_bp


def _safe_extract_zip(zip_ref, target_dir: str) -> None:
    """Safely extract a ZIP archive, preventing zip-slip."""
    abs_target = os.path.abspath(target_dir)
    for member in zip_ref.namelist():
        member_path = os.path.abspath(os.path.join(abs_target, member))
        if not member_path.startswith(abs_target + os.sep) and member_path != abs_target:
            raise ValueError(f"Unsafe zip entry: {member}")
    zip_ref.extractall(abs_target)


# Sports API endpoints
@api_bp.route("/api/sports", methods=["GET"])
def get_sports_data():
    """Get all sports data."""
    from hub.services import sports as sports_service

    sports_data = sports_service.get_sports_data()
    return jsonify(sports_data.to_dict())


@api_bp.route("/api/sports/ticker", methods=["GET"])
def get_sports_ticker_data():
    """Get sports ticker data."""
    # Get favorite teams from config
    from flask import current_app

    from hub.services import sports_ticker_service
    from hub.utils.config_helpers import get_favorite_teams_from_config

    config = current_app.config.get("CONFIG")
    if config:
        favorite_teams = get_favorite_teams_from_config(config)
    else:
        favorite_teams = []

    sports_ticker_data = sports_ticker_service.get_sports_ticker_data(
        favorite_teams,
        cache_only=True,
    )
    return jsonify(sports_ticker_data)


@api_bp.route("/api/sports/refresh", methods=["POST"])
def refresh_sports_data():
    """Manually refresh sports data."""
    from hub.services import sports as sports_service

    success = sports_service.refresh_sports_data()
    if success:
        sports_data = sports_service.get_sports_data()
        config = current_app.config.get("CONFIG")
        # Convert Pydantic model to dictionary for JSON serialization
        config_dict = get_config_dict(config)
        return render_template("partials/sports_ticker.html", sports_data=sports_data, config=config_dict)
    else:
        return jsonify({"error": "Failed to refresh sports data"}), 500


@api_bp.route("/api/sports/ticker/refresh", methods=["POST"])
def refresh_sports_ticker_data():
    """Manually refresh sports ticker data using file-based cache."""
    from hub.services import sports_ticker_service

    data = request.get_json(silent=True) or {}
    async_dispatch = bool(data.get("async", data.get("async_dispatch", False)))

    if async_dispatch:
        config = current_app.config.get("CONFIG")
        if config:
            from hub.utils.config_helpers import get_favorite_teams_from_config

            favorite_teams = get_favorite_teams_from_config(config)
        else:
            favorite_teams = []

        if sports_ticker_service.request_background_refresh(favorite_teams):
            return jsonify({"status": "queued", "message": "Sports ticker refresh queued"}), 202
        return jsonify({"status": "error", "message": "Unable to queue refresh"}), 500

    success = sports_ticker_service.refresh_sports_ticker_data()
    if success:
        # Get the refreshed data
        sports_data = sports_ticker_service.get_sports_ticker_data()
        config = current_app.config.get("CONFIG")
        # Convert Pydantic model to dictionary for JSON serialization
        config_dict = get_config_dict(config)
        return render_template("partials/sports_horizontal_ticker.html", sports_data=sports_data, config=config_dict)
    else:
        return jsonify({"error": "Failed to refresh sports ticker data"}), 500


@api_bp.route("/api/sports/last-updated", methods=["GET"])
def get_sports_last_updated():
    """Get the last updated time for sports data."""
    from hub.services import sports as sports_service

    sports_data = sports_service.get_sports_data()
    if sports_data.last_updated:
        # Format time to show how long ago it was updated
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        # Ensure sports_data.last_updated is timezone-aware
        last_updated = sports_data.last_updated
        if last_updated.tzinfo is None:
            # If it's naive, assume it's UTC
            from datetime import timezone as tz

            last_updated = last_updated.replace(tzinfo=tz.utc)

        time_diff = now - last_updated
        minutes_ago = int(time_diff.total_seconds() // 60)

        if minutes_ago < 1:
            return "Updated just now"
        elif minutes_ago == 1:
            return "Updated 1 minute ago"
        else:
            return f"Updated {minutes_ago} minutes ago"
    return "Unknown"


@api_bp.route("/api/sports/favorite_teams", methods=["GET", "POST"])
def manage_favorite_teams():
    """Get or update the configured favorite teams."""
    if request.method == "GET":
        config = current_app.config.get("CONFIG")
        if config:
            from hub.utils.config_helpers import get_favorite_teams_from_config

            favorite_teams = get_favorite_teams_from_config(config)
            return jsonify({"favorite_teams": favorite_teams})
        else:
            return jsonify({"favorite_teams": []})
    elif request.method == "POST":
        from hub.services import sports as sports_service

        data = request.get_json(silent=True) or {}
        new_favorite_teams = data.get("favorite_teams", [])

        # Update favorite teams
        success = sports_service.update_favorite_teams(new_favorite_teams)

        if success:
            # Return updated sports data to refresh the view
            sports_data = sports_service.get_sports_data(new_favorite_teams)
            config = current_app.config.get("CONFIG")
            # Convert Pydantic model to dictionary for JSON serialization
            config_dict = get_config_dict(config)
            return render_template("partials/sports_ticker.html", sports_data=sports_data, config=config_dict)
        else:
            return jsonify({"error": "Failed to update favorite teams"}), 500


@api_bp.route("/api/sports/favorite_teams/add", methods=["POST"])
def add_favorite_team():
    """Add a team to favorite teams."""
    from hub.services import sports as sports_service

    # Handle both JSON and form data
    team_name = None
    if request.is_json:
        data = request.get_json(silent=True) or {}
        team_name = data.get("team_name") or data.get("custom-team-input") or data.get("value")
    else:
        team_name = (
            request.form.get("custom-team-input") or request.form.get("team_name") or request.values.get("value")
        )

    if not team_name:
        return jsonify({"error": "Team name is required"}), 400

    # Get current favorite teams
    config = current_app.config.get("CONFIG")
    if config:
        from hub.utils.config_helpers import get_favorite_teams_from_config

        current_favorite_teams = get_favorite_teams_from_config(config)
    else:
        current_favorite_teams = []

    # Add new team if not already in the list
    if team_name.lower() not in [team.lower() for team in current_favorite_teams]:
        current_favorite_teams = current_favorite_teams + [team_name.lower()]

    # Update favorite teams
    success = sports_service.update_favorite_teams(current_favorite_teams)

    if success:
        # Return updated team management view
        return render_template(
            "partials/sports_manage_teams.html", config=config, current_favorite_teams=current_favorite_teams
        )
    else:
        return jsonify({"error": "Failed to add favorite team"}), 500


@api_bp.route("/partials/sports/horizontal-ticker", methods=["GET"])
@require_default_rate_limit
def get_horizontal_sports_ticker():
    """Return horizontal sports ticker partial."""
    # Get favorite teams from config
    from flask import current_app

    from hub.services import sports_ticker_service
    from hub.utils.config_helpers import get_favorite_teams_from_config

    config = current_app.config.get("CONFIG")
    if config:
        favorite_teams = get_favorite_teams_from_config(config)
    else:
        favorite_teams = []

    sports_data = sports_ticker_service.get_sports_ticker_data(
        favorite_teams,
        cache_only=True,
    )
    config = current_app.config.get("CONFIG")

    # Convert Pydantic model to dictionary for JSON serialization
    config_dict = get_config_dict(config)

    return render_template("partials/sports_horizontal_ticker.html", sports_data=sports_data, config=config_dict)


# Admin API endpoints


# Webhook API endpoints


@api_bp.route("/api/webhooks", methods=["GET"])
@require_ip_whitelist
def get_webhooks():
    """Get all webhooks."""
    from hub.services import webhook

    webhooks = webhook.get_all_webhooks()
    return jsonify([w.to_dict() for w in webhooks]), 200


@api_bp.route("/api/webhooks", methods=["POST"])
@require_ip_whitelist
def create_webhook():
    """Create a new webhook."""
    from hub.services import webhook

    data = request.get_json(silent=True) or {}

    name = data.get("name")
    url = data.get("url")
    event_types = data.get("event_types", ["weather_alert"])
    active = data.get("active", True)
    secret = data.get("secret")
    headers = data.get("headers", {})

    if not name or not url:
        return jsonify({"error": "Name and URL are required"}), 400

    created_webhook = webhook.create_webhook(name, url, event_types, active, secret, headers)
    if created_webhook:
        return jsonify(created_webhook.to_dict()), 201
    else:
        return jsonify({"error": "Failed to create webhook"}), 500


@api_bp.route("/api/webhooks/<int:webhook_id>", methods=["GET"])
@require_ip_whitelist
def get_webhook(webhook_id):
    """Get a specific webhook."""
    from hub.services import webhook

    webhook_obj = webhook.get_webhook(webhook_id)
    if webhook_obj:
        return jsonify(webhook_obj.to_dict()), 200
    else:
        return jsonify({"error": "Webhook not found"}), 404


@api_bp.route("/api/webhooks/<int:webhook_id>", methods=["PUT"])
@require_ip_whitelist
def update_webhook(webhook_id):
    """Update a webhook."""
    from hub.services import webhook

    data = request.get_json(silent=True) or {}

    success = webhook.update_webhook(
        webhook_id,
        name=data.get("name"),
        url=data.get("url"),
        event_types=data.get("event_types"),
        active=data.get("active"),
        secret=data.get("secret"),
        headers=data.get("headers"),
    )

    if success:
        updated_webhook = webhook.get_webhook(webhook_id)
        return jsonify(updated_webhook.to_dict()), 200
    else:
        return jsonify({"error": "Failed to update webhook"}), 500


@api_bp.route("/api/webhooks/<int:webhook_id>", methods=["DELETE"])
@require_ip_whitelist
def delete_webhook(webhook_id):
    """Delete a webhook."""
    from hub.services import webhook

    success = webhook.delete_webhook(webhook_id)
    if success:
        return jsonify({"status": "deleted"}), 200
    else:
        return jsonify({"error": "Failed to delete webhook"}), 500


@api_bp.route("/api/webhooks/<int:webhook_id>/test", methods=["POST"])
@require_ip_whitelist
def test_webhook(webhook_id):
    """Test a specific webhook."""
    from hub.services import webhook

    result = webhook.test_webhook_connection(webhook_id)
    return jsonify(result), 200


@api_bp.route("/api/webhooks/<int:webhook_id>/trigger", methods=["POST"])
@require_ip_whitelist
def trigger_webhook_endpoint(webhook_id):
    """Trigger a specific webhook with custom payload."""
    from hub.services import webhook

    data = request.get_json(silent=True) or {}
    payload = data.get("payload", {})

    success = webhook.trigger_webhook(webhook_id, payload)
    if success:
        return jsonify({"status": "triggered", "webhook_id": webhook_id}), 200
    else:
        return jsonify({"status": "failed", "webhook_id": webhook_id}), 500


@api_bp.route("/api/webhooks/trigger-all", methods=["POST"])
@require_ip_whitelist
def trigger_webhooks_for_event_endpoint():
    """Trigger webhooks for a specific event type."""
    from hub.services import webhook

    data = request.get_json(silent=True) or {}
    event_type = data.get("event_type", "weather_alert")
    payload = data.get("payload", {})

    async_dispatch = bool(data.get("async", data.get("async_dispatch", False)))
    triggered_count = webhook.trigger_webhooks_for_event(event_type, payload, async_dispatch=async_dispatch)
    return jsonify({"status": "triggered", "event_type": event_type, "triggered_count": triggered_count}), 200


@api_bp.route("/api/webhooks/<int:webhook_id>/logs", methods=["GET"])
@require_ip_whitelist
def get_webhook_logs(webhook_id):
    """Get logs for a specific webhook."""
    from hub.services import webhook

    logs = webhook.get_webhook_logs(webhook_id)
    return jsonify([log.to_dict() for log in logs]), 200


@api_bp.route("/api/webhooks/logs", methods=["GET"])
@require_ip_whitelist
def get_all_webhook_logs():
    """Get all webhook logs."""
    from hub.services import webhook

    logs = webhook.get_all_webhook_logs()
    return jsonify([log.to_dict() for log in logs]), 200


# Weather Alert API endpoints


@api_bp.route("/api/weather-alerts", methods=["GET"])
@require_default_rate_limit
def get_weather_alerts():
    """Get current weather alerts."""
    from hub.services import weather_alert

    alerts = weather_alert.get_active_weather_alerts()
    return jsonify({"alerts": alerts}), 200


@api_bp.route("/api/weather-alerts/history", methods=["GET"])
@require_default_rate_limit
def get_weather_alert_history():
    """Get weather alert history."""
    from hub.services import weather_alert

    hours = int(request.args.get("hours", 24))
    if hours > 168:  # Limit to 1 week max
        hours = 168

    alerts = weather_alert.get_weather_alert_history(hours)
    return jsonify({"alerts": alerts}), 200


@api_bp.route("/api/weather-alerts/check", methods=["POST"])
@require_admin_rate_limit
def check_weather_alerts():
    """Manually check for weather alerts."""
    from hub.services import weather_alert

    result = weather_alert.process_weather_alerts()
    return jsonify(result), 200


@api_bp.route("/api/weather-alerts/severity", methods=["GET"])
@require_default_rate_limit
def get_weather_severity():
    """Get current weather severity level."""
    from hub.services import weather_alert

    is_severe = weather_alert.is_weather_severe()
    current_weather = weather_alert.get_current_weather_data()

    return jsonify({"is_severe": is_severe, "current_weather": current_weather}), 200


# Plugin API endpoints


@api_bp.route("/api/plugins", methods=["GET"])
@require_ip_whitelist
def get_plugins():
    """Get all installed plugins."""
    installed_plugins = plugin_manager.get_installed_plugins()
    plugin_list = []

    for plugin_name in installed_plugins:
        plugin = plugin_manager.get_plugin(plugin_name)
        if plugin:
            plugin_list.append({"name": plugin_name, "info": plugin.get_metadata(), "enabled": plugin.enabled})
        else:
            plugin_list.append(
                {"name": plugin_name, "info": {"name": plugin_name, "status": "installed"}, "enabled": False}
            )

    return jsonify({"plugins": plugin_list, "enabled_plugins": plugin_manager.get_enabled_plugins()}), 200


@api_bp.route("/api/plugins/<plugin_name>", methods=["GET"])
@require_ip_whitelist
def get_plugin(plugin_name):
    """Get information about a specific plugin."""
    plugin = plugin_manager.get_plugin(plugin_name)
    if not plugin:
        return jsonify({"error": "Plugin not found"}), 404

    return jsonify({"name": plugin_name, "info": plugin.get_metadata(), "enabled": plugin.enabled}), 200


@api_bp.route("/api/plugins", methods=["POST"])
@require_ip_whitelist
def install_plugin():
    """Install a plugin from marketplace or upload."""
    data = request.get_json(silent=True) or {}

    if "plugin_name" in data:
        # Install from marketplace
        plugin_name = data["plugin_name"]
        marketplace = PluginMarketplace(plugin_manager)
        success = marketplace.install_plugin_from_marketplace(plugin_name)

        if success:
            # Load the newly installed plugin
            load_result = plugin_manager.load_plugin(plugin_name)
            if load_result.success:
                plugin_manager.initialize_plugin(plugin_name)
                return (
                    jsonify(
                        {"status": "success", "message": f"Plugin {plugin_name} installed and loaded successfully"}
                    ),
                    200,
                )
            else:
                return (
                    jsonify(
                        {
                            "status": "partial",
                            "message": f"Plugin {plugin_name} installed but failed to load: {load_result.message}",
                        }
                    ),
                    200,
                )
        else:
            return jsonify({"status": "error", "message": f"Failed to install plugin {plugin_name}"}), 500
    elif "plugin_data" in data or request.files:
        # Install from uploaded file
        try:
            if "plugin_file" in request.files:
                file = request.files["plugin_file"]
                if file.filename and file.filename.endswith(".zip"):
                    # Save to temporary location and extract
                    import os
                    import tempfile
                    import zipfile

                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_file_path = os.path.join(temp_dir, file.filename)
                        file.save(temp_file_path)

                        # Extract to plugin directory
                        plugin_dir = os.path.join(plugin_manager.plugin_directory, "temp_plugin")
                        with zipfile.ZipFile(temp_file_path, "r") as zip_ref:
                            _safe_extract_zip(zip_ref, plugin_dir)

                        # Get plugin name from directory structure or metadata
                        extracted_dirs = os.listdir(plugin_dir)
                        if extracted_dirs:
                            actual_plugin_dir = os.path.join(plugin_dir, extracted_dirs[0])
                            plugin_name = os.path.basename(actual_plugin_dir)

                            # Move to final location
                            final_plugin_dir = os.path.join(plugin_manager.plugin_directory, plugin_name)
                            if os.path.exists(actual_plugin_dir):
                                import shutil

                                if os.path.exists(final_plugin_dir):
                                    shutil.rmtree(final_plugin_dir)
                                shutil.move(actual_plugin_dir, final_plugin_dir)

                                # Clean up temp
                                shutil.rmtree(plugin_dir)

                                # Load the plugin
                                load_result = plugin_manager.load_plugin(plugin_name)
                                if load_result.success:
                                    plugin_manager.initialize_plugin(plugin_name)
                                    return (
                                        jsonify(
                                            {
                                                "status": "success",
                                                "message": f"Plugin {plugin_name} uploaded and loaded successfully",
                                            }
                                        ),
                                        200,
                                    )
                                else:
                                    return (
                                        jsonify(
                                            {
                                                "status": "partial",
                                                "message": f"Plugin {plugin_name} uploaded but failed to load: {load_result.message}",
                                            }
                                        ),
                                        200,
                                    )

            return jsonify({"status": "error", "message": "Invalid plugin file"}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": f"Error installing plugin: {str(e)}"}), 500
    else:
        return jsonify({"status": "error", "message": "No plugin specified"}), 400


@api_bp.route("/api/plugins/<plugin_name>", methods=["DELETE"])
@require_ip_whitelist
def uninstall_plugin(plugin_name):
    """Uninstall a plugin."""
    # First disable the plugin
    plugin_manager.disable_plugin(plugin_name)

    # Then unload the plugin
    success = plugin_manager.unload_plugin(plugin_name)

    # Remove from filesystem
    import os
    import shutil

    plugin_path = os.path.join(plugin_manager.plugin_directory, plugin_name)
    if os.path.exists(plugin_path):
        try:
            shutil.rmtree(plugin_path)
        except Exception as e:
            return jsonify({"status": "error", "message": f"Plugin disabled but could not remove files: {str(e)}"}), 500

    if success:
        return jsonify({"status": "success", "message": f"Plugin {plugin_name} uninstalled successfully"}), 200
    else:
        return jsonify({"status": "error", "message": f"Failed to uninstall plugin {plugin_name}"}), 500


@api_bp.route("/api/plugins/<plugin_name>/enable", methods=["POST"])
@require_ip_whitelist
def enable_plugin(plugin_name):
    """Enable a plugin."""
    success = plugin_manager.enable_plugin(plugin_name)

    if success:
        return jsonify({"status": "success", "message": f"Plugin {plugin_name} enabled successfully"}), 200
    else:
        return jsonify({"status": "error", "message": f"Failed to enable plugin {plugin_name}"}), 500


@api_bp.route("/api/plugins/<plugin_name>/disable", methods=["POST"])
@require_ip_whitelist
def disable_plugin(plugin_name):
    """Disable a plugin."""
    success = plugin_manager.disable_plugin(plugin_name)

    if success:
        return jsonify({"status": "success", "message": f"Plugin {plugin_name} disabled successfully"}), 200
    else:
        return jsonify({"status": "error", "message": f"Failed to disable plugin {plugin_name}"}), 500


@api_bp.route("/api/plugins/<plugin_name>/reload", methods=["POST"])
@require_ip_whitelist
def reload_plugin(plugin_name):
    """Reload a plugin."""
    # First disable and unload
    plugin_manager.disable_plugin(plugin_name)
    plugin_manager.unload_plugin(plugin_name)

    # Re-load the plugin
    result = plugin_manager.load_plugin(plugin_name)

    if result.success:
        initialized = plugin_manager.initialize_plugin(plugin_name)
        if initialized:
            # Only enable if it was enabled before
            plugin = plugin_manager.get_plugin(plugin_name)
            if plugin and plugin.enabled:
                plugin_manager.enable_plugin(plugin_name)

        return (
            jsonify(
                {
                    "status": "success",
                    "message": f"Plugin {plugin_name} reloaded successfully",
                    "plugin_info": result.plugin.get_metadata() if result.plugin else None,
                }
            ),
            200,
        )
    else:
        return jsonify({"status": "error", "message": f"Failed to reload plugin {plugin_name}: {result.message}"}), 500


@api_bp.route("/api/plugins/marketplace", methods=["GET"])
@require_ip_whitelist
def get_marketplace_plugins():
    """Get available plugins from marketplace."""
    marketplace = PluginMarketplace(plugin_manager)
    plugins = marketplace.get_available_plugins()

    result = []
    for plugin in plugins:
        result.append(
            {
                "name": plugin.name,
                "version": plugin.version,
                "author": plugin.author,
                "description": plugin.description,
                "type": plugin.type.value,
                "rating": plugin.rating,
                "downloads": plugin.downloads,
                "last_updated": plugin.last_updated,
            }
        )

    return jsonify({"plugins": result}), 200


@api_bp.route("/api/plugins/marketplace/search", methods=["GET"])
@require_ip_whitelist
def search_marketplace():
    """Search for plugins in marketplace."""
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Query parameter required"}), 400

    marketplace = PluginMarketplace(plugin_manager)
    plugins = marketplace.search_plugins(query)

    result = []
    for plugin in plugins:
        result.append(
            {
                "name": plugin.name,
                "version": plugin.version,
                "author": plugin.author,
                "description": plugin.description,
                "type": plugin.type.value,
                "rating": plugin.rating,
                "downloads": plugin.downloads,
                "last_updated": plugin.last_updated,
            }
        )

    return jsonify({"plugins": result}), 200


@api_bp.route("/api/plugins/check-updates", methods=["GET"])
@require_ip_whitelist
def check_plugin_updates():
    """Check for available plugin updates."""
    marketplace = PluginMarketplace(plugin_manager)
    updates = marketplace.check_for_updates()

    return jsonify({"updates": updates}), 200


@api_bp.route("/api/plugins/<plugin_name>/update", methods=["POST"])
@require_ip_whitelist
def update_plugin(plugin_name):
    """Update a specific plugin."""
    marketplace = PluginMarketplace(plugin_manager)

    # Check if update is available
    updates = marketplace.check_for_updates()
    if plugin_name not in updates:
        return jsonify({"status": "no_update", "message": f"No update available for {plugin_name}"}), 200

    # Uninstall current version
    plugin_manager.disable_plugin(plugin_name)
    plugin_manager.unload_plugin(plugin_name)

    # Install the new version
    success = marketplace.install_plugin_from_marketplace(plugin_name)

    if success:
        # Load the updated plugin
        result = plugin_manager.load_plugin(plugin_name)
        if result.success:
            plugin_manager.initialize_plugin(plugin_name)
            # If the original was enabled, enable the new version too
            if plugin_name in plugin_manager.get_enabled_plugins():
                plugin_manager.enable_plugin(plugin_name)

            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f"Plugin {plugin_name} updated successfully",
                        "new_version": updates[plugin_name],
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "status": "partial",
                        "message": f"Plugin {plugin_name} updated but failed to load: {result.message}",
                    }
                ),
                200,
            )
    else:
        return jsonify({"status": "error", "message": f"Failed to update plugin {plugin_name}"}), 500


# IoT API endpoints


@api_bp.route("/api/iot/devices", methods=["GET"])
@require_default_rate_limit
def get_iot_devices():
    """Get all IoT devices with optional filtering."""
    from hub.services.iot_service import iot_service

    device_type = (request.args.get("type") or "").strip()
    active = request.args.get("active")

    if device_type:
        devices = iot_service.get_devices_by_type(device_type)
    else:
        devices = iot_service.get_all_devices()

    if active is not None:
        active_flag = active.lower() in ["true", "1", "yes", "on"]
        devices = [device for device in devices if bool(device.is_active) == active_flag]

    return jsonify([device.to_dict() for device in devices]), 200


@api_bp.route("/api/iot/devices/<int:device_id>", methods=["GET"])
@require_default_rate_limit
def get_iot_device(device_id):
    """Get a specific IoT device."""
    from hub.services.iot_service import iot_service

    device = iot_service.get_device(device_id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    return jsonify(device.to_dict()), 200


@api_bp.route("/api/iot/devices", methods=["POST"])
@require_admin_rate_limit
def create_iot_device():
    """Add a new IoT device."""
    from hub.services.iot_service import iot_service

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    device_type = (data.get("device_type") or "").strip()
    device_identifier = (data.get("device_id") or "").strip()

    if not name or not device_type or not device_identifier:
        return jsonify({"error": "name, device_type, and device_id are required"}), 400

    host = data.get("host")
    port = data.get("port")
    config = data.get("config") if isinstance(data.get("config"), dict) else None

    if port is not None:
        try:
            port = int(port)
        except (TypeError, ValueError):
            return jsonify({"error": "port must be an integer"}), 400

    device = iot_service.add_device(
        name=name, device_type=device_type, device_id=device_identifier, host=host, port=port, config=config
    )

    if not device:
        return jsonify({"error": "Failed to add device"}), 500

    return jsonify(device.to_dict()), 201


@api_bp.route("/api/iot/devices/<int:device_id>", methods=["PUT"])
@require_admin_rate_limit
def update_iot_device(device_id):
    """Update an existing IoT device."""
    from hub.services.iot_service import iot_service

    data = request.get_json(silent=True) or {}
    is_active = data.get("is_active")
    if isinstance(is_active, str):
        is_active = is_active.lower() in ["true", "1", "yes", "on"]

    port = data.get("port")
    if port is not None:
        try:
            port = int(port)
        except (TypeError, ValueError):
            return jsonify({"error": "port must be an integer"}), 400

    device = iot_service.update_device(
        device_id=device_id,
        name=data.get("name"),
        device_type=data.get("device_type"),
        device_id_new=data.get("device_id"),
        host=data.get("host"),
        port=port,
        is_active=is_active,
        config=data.get("config") if isinstance(data.get("config"), dict) else None,
    )

    if not device:
        return jsonify({"error": "Device not found"}), 404

    return jsonify(device.to_dict()), 200


@api_bp.route("/api/iot/devices/<int:device_id>", methods=["DELETE"])
@require_admin_rate_limit
def delete_iot_device(device_id):
    """Delete an IoT device."""
    from hub.services.iot_service import iot_service

    success = iot_service.remove_device(device_id)
    if not success:
        return jsonify({"error": "Device not found"}), 404

    return jsonify({"status": "deleted"}), 200


@api_bp.route("/api/iot/devices/discover", methods=["POST"])
@require_admin_rate_limit
def discover_iot_devices():
    """Discover IoT devices on the network."""
    from hub.services.iot_service import iot_service

    data = request.get_json(silent=True) or {}
    async_flag = data.get("async")
    if async_flag is None:
        async_flag = True
    elif isinstance(async_flag, str):
        async_flag = async_flag.lower() in ["true", "1", "yes", "on"]

    if async_flag:
        queued = iot_service.request_background_discovery()
        if not queued:
            return jsonify({"status": "error", "message": "Failed to queue discovery"}), 500
        return jsonify({"status": "queued"}), 202

    devices = iot_service.discover_devices()
    return jsonify([device.to_dict() for device in devices]), 200


@api_bp.route("/api/iot/devices/<int:device_id>/command", methods=["POST"])
@require_admin_rate_limit
def send_iot_device_command(device_id):
    """Send a command to a specific IoT device."""
    from hub.services.iot_service import iot_service

    data = request.get_json(silent=True) or {}
    command = (data.get("command") or "").strip()
    params = data.get("params")

    if not command:
        return jsonify({"error": "command is required"}), 400

    success = iot_service.send_command_to_device(device_id, command, params)
    if not success:
        return jsonify({"error": "Command failed"}), 500

    return jsonify({"status": "success"}), 200


# Casting API endpoints


@api_bp.route("/api/casting/devices", methods=["GET"])
@require_default_rate_limit
def get_casting_devices():
    """Get all available casting devices."""
    devices = media.get_casting_devices()
    return jsonify([device.to_dict() for device in devices]), 200


@api_bp.route("/api/casting/devices/<device_id>", methods=["GET"])
@require_default_rate_limit
def get_casting_device(device_id):
    """Get a specific casting device."""
    device = media.get_casting_device(device_id)
    if device:
        return jsonify(device.to_dict()), 200
    else:
        return jsonify({"error": "Device not found"}), 404


@api_bp.route("/api/casting/devices/discover", methods=["GET"])
@require_default_rate_limit
def discover_casting_devices():
    """Discover casting devices on the network."""
    devices = media.discover_casting_devices()

    # Add newly discovered devices to the database
    for device in devices:
        casting_manager.create_device(device)

    # Refresh device list to update timestamps and statuses
    casting_manager.refresh_device_list()

    return jsonify([device.to_dict() for device in devices]), 200


@api_bp.route("/api/casting/devices/<device_id>/play", methods=["POST"])
@require_default_rate_limit
def play_media_on_device_endpoint(device_id):
    """Play media on a specific casting device."""
    data = request.get_json(silent=True) or {}
    media_url = data.get("media_url")
    content_type = data.get("content_type", "video/mp4")

    if not media_url:
        return jsonify({"error": "Media URL is required"}), 400

    success = media.play_media_on_device(device_id, media_url, content_type)
    if success:
        return jsonify({"status": "success", "message": f"Media playing on device {device_id}"}), 200
    else:
        return jsonify({"status": "error", "message": f"Failed to play media on device {device_id}"}), 500


@api_bp.route("/api/casting/devices/<device_id>/pause", methods=["POST"])
@require_default_rate_limit
def pause_media_on_device_endpoint(device_id):
    """Pause media on a specific casting device."""
    config = current_app.config.get("CONFIG")
    if not config or not hasattr(config, "casting") or not config.casting.enabled:
        return jsonify({"error": "Casting is not enabled"}), 400

    adapter = casting_manager.get_adapter_for_device(device_id)
    if not adapter:
        return jsonify({"error": f"No adapter found for device {device_id}"}), 400

    success = adapter.pause()
    if success:
        return jsonify({"status": "success", "message": f"Media paused on device {device_id}"}), 200
    else:
        return jsonify({"status": "error", "message": f"Failed to pause media on device {device_id}"}), 500


@api_bp.route("/api/casting/devices/<device_id>/stop", methods=["POST"])
@require_default_rate_limit
def stop_media_on_device_endpoint(device_id):
    """Stop media on a specific casting device."""
    config = current_app.config.get("CONFIG")
    if not config or not hasattr(config, "casting") or not config.casting.enabled:
        return jsonify({"error": "Casting is not enabled"}), 400

    adapter = casting_manager.get_adapter_for_device(device_id)
    if not adapter:
        return jsonify({"error": f"No adapter found for device {device_id}"}), 404

    success = adapter.stop()
    if success:
        return jsonify({"status": "success", "message": f"Media stopped on device {device_id}"}), 200
    else:
        return jsonify({"status": "error", "message": f"Failed to stop media on device {device_id}"}), 500


@api_bp.route("/api/casting/devices/<device_id>/volume", methods=["PUT"])
@require_default_rate_limit
def set_volume_on_device_endpoint(device_id):
    """Set volume on a specific casting device."""
    config = current_app.config.get("CONFIG")
    if not config or not hasattr(config, "casting") or not config.casting.enabled:
        return jsonify({"error": "Casting is not enabled"}), 400

    data = request.get_json(silent=True) or {}
    volume = data.get("volume")

    if volume is None or not (0 <= volume <= 100):
        return jsonify({"error": "Volume must be between 0 and 100"}), 400

    # Convert to 0.0-1.0 scale for Google Cast
    volume_level = volume / 100.0

    adapter = casting_manager.get_adapter_for_device(device_id)
    if not adapter:
        return jsonify({"error": f"No adapter found for device {device_id}"}), 404

    success = adapter.set_volume(volume_level)
    if success:
        return jsonify({"status": "success", "volume": volume}), 200
    else:
        return jsonify({"status": "error", "message": f"Failed to set volume on device {device_id}"}), 500


@api_bp.route("/api/casting/devices/<device_id>/status", methods=["GET"])
@require_default_rate_limit
def get_device_status_endpoint(device_id):
    """Get status of a specific casting device."""
    config = current_app.config.get("CONFIG")
    if not config or not hasattr(config, "casting") or not config.casting.enabled:
        return jsonify({"error": "Casting is not enabled"}), 400

    adapter = casting_manager.get_adapter_for_device(device_id)
    if not adapter:
        return jsonify({"error": f"No adapter found for device {device_id}"}), 404

    if adapter.is_connected():
        device_info = adapter.get_device_info()
        media_status = adapter.get_media_status()

        status = {
            "device_connected": True,
            "device_info": device_info,
            "media_status": media_status.to_dict() if media_status else None,
        }
        return jsonify(status), 200
    else:
        return jsonify({"device_connected": False}), 200


@api_bp.route("/api/casting/groups", methods=["GET"])
@require_default_rate_limit
def get_casting_groups():
    """Get all casting groups."""
    groups = casting_manager.get_all_groups()
    return jsonify([group.to_dict() for group in groups]), 200


@api_bp.route("/api/casting/groups", methods=["POST"])
@require_default_rate_limit
def create_casting_group():
    """Create a new casting group."""
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    devices = data.get("devices", [])

    if not name:
        return jsonify({"error": "Group name is required"}), 400

    from hub.models import CastingGroup

    group = CastingGroup(name=name, devices=devices)
    success = casting_manager.create_group(group)

    if success:
        return jsonify({"status": "success", "message": f"Group {name} created"}), 201
    else:
        return jsonify({"status": "error", "message": "Failed to create group"}), 500


@api_bp.route("/api/casting/groups/<int:group_id>/play", methods=["POST"])
@require_default_rate_limit
def play_media_on_group_endpoint(group_id):
    """Play media on all devices in a group (multi-room audio)."""
    data = request.get_json(silent=True) or {}
    media_url = data.get("media_url")
    content_type = data.get("content_type", "video/mp4")

    if not media_url:
        return jsonify({"error": "Media URL is required"}), 400

    success = media.play_media_on_group(group_id, media_url, content_type)
    if success:
        return jsonify({"status": "success", "message": f"Media playing on group {group_id}"}), 200
    else:
        return jsonify({"status": "error", "message": f"Failed to play media on group {group_id}"}), 500


@api_bp.route("/api/casting/queue/<device_id>", methods=["GET"])
@require_default_rate_limit
def get_media_queue_endpoint(device_id):
    """Get the media queue for a device."""
    queue = media.get_media_queue(device_id)
    if queue:
        if hasattr(queue, "to_dict"):
            return jsonify(queue.to_dict()), 200
        return jsonify(queue), 200
    else:
        # Create an empty queue if none exists
        success = casting_manager.create_queue_for_device(device_id)
        if success:
            queue = media.get_media_queue(device_id)
            if queue:
                if hasattr(queue, "to_dict"):
                    return jsonify(queue.to_dict()), 200
                return jsonify(queue), 200

        return jsonify({"error": "Failed to get or create queue"}), 500


@api_bp.route("/api/casting/queue/<device_id>/add", methods=["POST"])
@require_default_rate_limit
def add_to_queue_endpoint(device_id):
    """Add a media item to the device's queue."""
    data = request.get_json(silent=True) or {}
    media_item = {
        "url": data.get("url"),
        "title": data.get("title", ""),
        "type": data.get("type", "video"),
        "duration": data.get("duration", 0),
    }

    if not media_item["url"]:
        return jsonify({"error": "Media URL is required"}), 400

    success = media.add_to_queue(device_id, media_item)
    if success:
        return jsonify({"status": "success", "message": "Media added to queue"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to add media to queue"}), 500


# Photo API endpoints


@api_bp.route("/api/photos", methods=["GET"])
@require_default_rate_limit
def get_photos():
    """Get all photos with optional pagination and filtering."""
    from hub.services import photo_service

    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    album_id = request.args.get("album_id", type=int)

    photos = photo_service.get_photos(limit=limit, offset=offset, album_id=album_id)
    return jsonify([photo.to_dict() for photo in photos]), 200


@api_bp.route("/api/photos/<int:photo_id>", methods=["GET"])
@require_default_rate_limit
def get_photo(photo_id):
    """Get a specific photo by ID."""
    from hub.services import photo_service

    photo = photo_service.get_photo_by_id(photo_id)
    if not photo:
        return jsonify({"error": "Photo not found"}), 404
    return jsonify(photo.to_dict()), 200


@api_bp.route("/api/photos", methods=["POST"])
@require_admin_rate_limit
def create_photo():
    """Create a new photo record."""
    from hub.services import photo_service

    data = request.get_json(silent=True) or {}

    title = data.get("title", "")
    filename = data.get("filename", "")
    description = data.get("description", "")
    date_taken_str = data.get("date_taken")
    source = data.get("source", "local")
    tags = data.get("tags", [])
    album_id = data.get("album_id")

    # Validate required fields
    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    # Parse date if provided
    date_taken = None
    if date_taken_str:
        try:
            date_taken = datetime.fromisoformat(date_taken_str.replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400

    photo = photo_service.create_photo(
        filename=filename,
        title=title,
        description=description,
        date_taken=date_taken,
        source=source,
        tags=tags,
        album_id=album_id,
    )

    if photo:
        return jsonify(photo.to_dict()), 201
    else:
        return jsonify({"error": "Failed to create photo"}), 500


@api_bp.route("/api/photos/<int:photo_id>", methods=["PUT"])
@require_admin_rate_limit
def update_photo(photo_id):
    """Update an existing photo."""
    from hub.services import photo_service

    data = request.get_json(silent=True) or {}

    result = photo_service.update_photo(
        photo_id=photo_id,
        title=data.get("title"),
        description=data.get("description"),
        tags=data.get("tags"),
        album_id=data.get("album_id"),
    )

    if result:
        return jsonify(result.to_dict()), 200
    else:
        return jsonify({"error": "Failed to update photo"}), 500


@api_bp.route("/api/photos/<int:photo_id>", methods=["DELETE"])
@require_admin_rate_limit
def delete_photo(photo_id):
    """Delete a photo."""
    from hub.services import photo_service

    success = photo_service.delete_photo(photo_id)
    if success:
        return jsonify({"status": "deleted"}), 200
    else:
        return jsonify({"error": "Failed to delete photo"}), 500


@api_bp.route("/api/albums", methods=["GET"])
@require_default_rate_limit
def get_albums():
    """Get all albums."""
    from hub.services import photo_service

    albums = photo_service.get_albums()
    return jsonify([album.to_dict() for album in albums]), 200


@api_bp.route("/api/albums", methods=["POST"])
@require_admin_rate_limit
def create_album():
    """Create a new album."""
    from hub.services import photo_service

    data = request.get_json(silent=True) or {}

    name = data.get("name", "")
    description = data.get("description", "")

    if not name:
        return jsonify({"error": "Name is required"}), 400

    album = photo_service.create_album(name, description)
    if album:
        return jsonify(album.to_dict()), 201
    else:
        return jsonify({"error": "Failed to create album"}), 500


@api_bp.route("/api/albums/<int:album_id>", methods=["GET"])
@require_default_rate_limit
def get_album(album_id):
    """Get a specific album by ID."""
    from hub.services import photo_service

    album = photo_service.get_album_by_id(album_id)
    if not album:
        return jsonify({"error": "Album not found"}), 404
    return jsonify(album.to_dict()), 200


@api_bp.route("/api/albums/<int:album_id>", methods=["PUT"])
@require_admin_rate_limit
def update_album(album_id):
    """Update an existing album."""
    from hub.services import photo_service

    data = request.get_json(silent=True) or {}

    result = photo_service.update_album(album_id=album_id, name=data.get("name"), description=data.get("description"))

    if result:
        return jsonify(result.to_dict()), 200
    else:
        return jsonify({"error": "Failed to update album"}), 500


@api_bp.route("/api/albums/<int:album_id>", methods=["DELETE"])
@require_admin_rate_limit
def delete_album(album_id):
    """Delete an album."""
    from hub.services import photo_service

    success = photo_service.delete_album(album_id)
    if success:
        return jsonify({"status": "deleted"}), 200
    else:
        return jsonify({"error": "Failed to delete album"}), 500


@api_bp.route("/api/photos/slideshow", methods=["GET"])
@require_default_rate_limit
def get_slideshow_photos():
    """Get photos for slideshow with optional filtering and pagination."""
    from hub.services import photo_service

    # Get pagination parameters
    limit = request.args.get("limit", 10, type=int)  # Default to 10 photos per request
    offset = request.args.get("offset", 0, type=int)
    album_id = request.args.get("album_id", type=int)
    shuffle = request.args.get("shuffle", "true").lower() == "true"

    # For slideshow, we need to modify the service to support pagination
    photos = photo_service.get_photos_for_slideshow_with_pagination(
        album_id=album_id, shuffle=shuffle, limit=limit, offset=offset
    )
    return jsonify([photo.to_dict() for photo in photos]), 200


@api_bp.route("/api/photos/sync", methods=["POST"])
@require_admin_rate_limit
def sync_photos():
    """Sync photos from configured sources."""
    from hub.services import photo_service

    success = photo_service.sync_photos_from_sources()
    if success:
        return jsonify({"status": "success", "message": "Photos synced successfully"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to sync photos"}), 500


# Music API endpoints


@api_bp.route("/api/music/tracks", methods=["GET"])
@require_default_rate_limit
def get_music_tracks():
    """Get all music tracks with optional pagination and filtering."""
    from hub.services import music_service

    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    playlist_id = request.args.get("playlist_id", type=int)
    genre = request.args.get("genre")

    tracks = music_service.get_tracks(limit=limit, offset=offset, playlist_id=playlist_id, genre=genre)
    return jsonify([track.to_dict() for track in tracks]), 200


@api_bp.route("/api/music/tracks/<int:track_id>", methods=["GET"])
@require_default_rate_limit
def get_music_track(track_id):
    """Get a specific music track by ID."""
    from hub.services import music_service

    track = music_service.get_track_by_id(track_id)
    if not track:
        return jsonify({"error": "Track not found"}), 404
    return jsonify(track.to_dict()), 200


@api_bp.route("/api/music/tracks", methods=["POST"])
@require_admin_rate_limit
def create_music_track():
    """Create a new music track."""
    from hub.services import music_service

    data = request.get_json(silent=True) or {}

    title = data.get("title", "")
    artist = data.get("artist", "")
    album = data.get("album", "")
    genre = data.get("genre")
    duration = data.get("duration")
    source = data.get("source", "local")
    album_art_url = data.get("album_art_url")

    # Validate required fields
    if not title or not artist:
        return jsonify({"error": "Title and artist are required"}), 400

    track = music_service.create_track(
        title=title,
        artist=artist,
        album=album,
        genre=genre,
        duration=duration,
        source=source,
        album_art_url=album_art_url,
    )

    if track:
        return jsonify(track.to_dict()), 201
    else:
        return jsonify({"error": "Failed to create track"}), 500


@api_bp.route("/api/music/tracks/<int:track_id>", methods=["PUT"])
@require_admin_rate_limit
def update_music_track(track_id):
    """Update an existing music track."""
    from hub.services import music_service

    data = request.get_json(silent=True) or {}

    result = music_service.update_track(
        track_id=track_id,
        title=data.get("title"),
        artist=data.get("artist"),
        album=data.get("album"),
        genre=data.get("genre"),
        duration=data.get("duration"),
        album_art_url=data.get("album_art_url"),
    )

    if result:
        return jsonify(result.to_dict()), 200
    else:
        return jsonify({"error": "Failed to update track"}), 500


@api_bp.route("/api/music/tracks/<int:track_id>", methods=["DELETE"])
@require_admin_rate_limit
def delete_music_track(track_id):
    """Delete a music track."""
    from hub.services import music_service

    success = music_service.delete_track(track_id)
    if success:
        return jsonify({"status": "deleted"}), 200
    else:
        return jsonify({"error": "Failed to delete track"}), 500


@api_bp.route("/api/music/playlists", methods=["GET"])
@require_default_rate_limit
def get_music_playlists():
    """Get all playlists."""
    from hub.services import music_service

    playlists = music_service.get_playlists()
    return jsonify([playlist.to_dict() for playlist in playlists]), 200


@api_bp.route("/api/music/playlists", methods=["POST"])
@require_admin_rate_limit
def create_music_playlist():
    """Create a new playlist."""
    from hub.services import music_service

    data = request.get_json(silent=True) or {}

    name = data.get("name", "")
    description = data.get("description", "")

    if not name:
        return jsonify({"error": "Name is required"}), 400

    playlist = music_service.create_playlist(name, description)
    if playlist:
        return jsonify(playlist.to_dict()), 201
    else:
        return jsonify({"error": "Failed to create playlist"}), 500


@api_bp.route("/api/music/playlists/<int:playlist_id>", methods=["GET"])
@require_default_rate_limit
def get_music_playlist(playlist_id):
    """Get a specific playlist by ID."""
    from hub.services import music_service

    playlist = music_service.get_playlist_by_id(playlist_id)
    if not playlist:
        return jsonify({"error": "Playlist not found"}), 404
    return jsonify(playlist.to_dict()), 200


@api_bp.route("/api/music/playlists/<int:playlist_id>", methods=["PUT"])
@require_admin_rate_limit
def update_music_playlist(playlist_id):
    """Update an existing playlist."""
    from hub.services import music_service

    data = request.get_json(silent=True) or {}

    result = music_service.update_playlist(
        playlist_id=playlist_id, name=data.get("name"), description=data.get("description")
    )

    if result:
        return jsonify(result.to_dict()), 200
    else:
        return jsonify({"error": "Failed to update playlist"}), 500


@api_bp.route("/api/music/playlists/<int:playlist_id>", methods=["DELETE"])
@require_admin_rate_limit
def delete_music_playlist(playlist_id):
    """Delete a playlist."""
    from hub.services import music_service

    success = music_service.delete_playlist(playlist_id)
    if success:
        return jsonify({"status": "deleted"}), 200
    else:
        return jsonify({"error": "Failed to delete playlist"}), 500


@api_bp.route("/api/music/playlists/<int:playlist_id>/tracks", methods=["GET"])
@require_default_rate_limit
def get_tracks_in_playlist(playlist_id):
    """Get all tracks in a specific playlist."""
    from hub.services import music_service

    tracks = music_service.get_tracks_in_playlist(playlist_id)
    return jsonify([track.to_dict() for track in tracks]), 200


@api_bp.route("/api/music/playlists/<int:playlist_id>/tracks", methods=["POST"])
@require_admin_rate_limit
def add_track_to_playlist(playlist_id):
    """Add a track to a specific playlist."""
    from hub.services import music_service

    data = request.get_json(silent=True) or {}

    track_id = data.get("track_id")
    if not track_id:
        return jsonify({"error": "Track ID is required"}), 400

    success = music_service.add_track_to_playlist(playlist_id, track_id)
    if success:
        return jsonify({"status": "success", "message": "Track added to playlist"}), 200
    else:
        return jsonify({"error": "Failed to add track to playlist"}), 500


@api_bp.route("/api/music/playlists/<int:playlist_id>/tracks/<int:track_id>", methods=["DELETE"])
@require_admin_rate_limit
def remove_track_from_playlist(playlist_id, track_id):
    """Remove a track from a specific playlist."""
    from hub.services import music_service

    success = music_service.remove_track_from_playlist(playlist_id, track_id)
    if success:
        return jsonify({"status": "removed", "message": "Track removed from playlist"}), 200
    else:
        return jsonify({"error": "Failed to remove track from playlist"}), 500


@api_bp.route("/api/music/queues", methods=["POST"])
@require_default_rate_limit
def create_music_queue():
    """Create a new music queue."""
    from hub.services import music_service

    data = request.get_json(silent=True) or {}

    playlist_id = data.get("playlist_id")

    queue = music_service.create_queue(playlist_id)
    if queue:
        return jsonify(queue.to_dict()), 201
    else:
        return jsonify({"error": "Failed to create queue"}), 500


@api_bp.route("/api/music/queues/<int:queue_id>", methods=["GET"])
@require_default_rate_limit
def get_music_queue(queue_id):
    """Get a specific music queue by ID."""
    from hub.services import music_service

    queue = music_service.get_queue_by_id(queue_id)
    if not queue:
        return jsonify({"error": "Queue not found"}), 404
    return jsonify(queue.to_dict()), 200


@api_bp.route("/api/music/queues/<int:queue_id>", methods=["PUT"])
@require_admin_rate_limit
def update_music_queue(queue_id):
    """Update a music queue."""
    from hub.services import music_service

    data = request.get_json(silent=True) or {}

    result = music_service.update_queue(
        queue_id=queue_id,
        queue_items=data.get("queue_items"),
        current_item_index=data.get("current_item_index"),
        is_playing=data.get("is_playing"),
        volume=data.get("volume"),
    )

    if result:
        return jsonify(result.to_dict()), 200
    else:
        return jsonify({"error": "Failed to update queue"}), 500


@api_bp.route("/api/music/queues/<int:queue_id>/play", methods=["POST"])
@require_default_rate_limit
def play_music_queue(queue_id):
    """Start playing a music queue."""
    from hub.services import music_service

    success = music_service.play_queue(queue_id)
    if success:
        return jsonify({"status": "playing"}), 200
    else:
        return jsonify({"error": "Failed to play queue"}), 500


@api_bp.route("/api/music/queues/<int:queue_id>/pause", methods=["POST"])
@require_default_rate_limit
def pause_music_queue(queue_id):
    """Pause a music queue."""
    from hub.services import music_service

    success = music_service.pause_queue(queue_id)
    if success:
        return jsonify({"status": "paused"}), 200
    else:
        return jsonify({"error": "Failed to pause queue"}), 500


@api_bp.route("/api/music/queues/<int:queue_id>/tracks", methods=["POST"])
@require_default_rate_limit
def add_track_to_queue(queue_id):
    """Add a track to a music queue."""
    from hub.services import music_service

    data = request.get_json(silent=True) or {}

    track_id = data.get("track_id")
    if not track_id:
        return jsonify({"error": "Track ID is required"}), 400

    success = music_service.add_track_to_queue(queue_id, track_id)
    if success:
        return jsonify({"status": "success", "message": "Track added to queue"}), 200
    else:
        return jsonify({"error": "Failed to add track to queue"}), 500


@api_bp.route("/api/music/sync", methods=["POST"])
@require_admin_rate_limit
def sync_music_tracks():
    """Sync music tracks from configured sources."""
    from hub.services import music_service

    success = music_service.sync_tracks_from_sources()
    if success:
        return jsonify({"status": "success", "message": "Music tracks synced successfully"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to sync music tracks"}), 500


# Miniplayer API endpoints
@api_bp.route("/api/music/current", methods=["GET"])
@require_default_rate_limit
def get_current_track():
    """Get the currently playing track information."""
    from hub.services import music_controller

    # Get the current playback state from the controller
    state = music_controller.get_playback_state()
    return jsonify(state), 200


@api_bp.route("/api/music/play", methods=["POST"])
@require_default_rate_limit
def play_current_track():
    """Start playing the current track."""
    from hub.services import music_controller

    # Start playback via the controller
    if music_controller.play():
        state = music_controller.get_playback_state()
        return jsonify(state), 200
    else:
        return jsonify({"error": "No track to play"}), 400


@api_bp.route("/api/music/pause", methods=["POST"])
@require_default_rate_limit
def pause_current_track():
    """Pause the current track."""
    from hub.services import music_controller

    # Pause playback via the controller
    if music_controller.pause():
        state = music_controller.get_playback_state()
        return jsonify(state), 200
    else:
        return jsonify({"error": "Failed to pause playback"}), 400


@api_bp.route("/api/music/next", methods=["POST"])
@require_default_rate_limit
def next_track():
    """Skip to the next track."""
    from hub.services import music_controller

    # Go to next track via the controller
    next_track = music_controller.next_track()
    if next_track:
        state = music_controller.get_playback_state()
        return jsonify(state), 200
    else:
        return jsonify({"error": "No next track available"}), 404


@api_bp.route("/api/music/previous", methods=["POST"])
@require_default_rate_limit
def previous_track():
    """Go back to the previous track."""
    from hub.services import music_controller

    # Go to previous track via the controller
    prev_track = music_controller.previous_track()
    if prev_track:
        state = music_controller.get_playback_state()
        return jsonify(state), 200
    else:
        return jsonify({"error": "No previous track available"}), 404


@api_bp.route("/api/music/seek", methods=["POST"])
@require_default_rate_limit
def seek_track():
    """Seek to a specific time in the current track."""
    from hub.services import music_controller

    data = request.get_json(silent=True) or {}
    time = data.get("time", 0)

    # Seek to the specified time
    actual_time = music_controller.seek_to(time)
    return jsonify({"status": "success", "current_time": actual_time}), 200


@api_bp.route("/api/music/tracks/<int:track_id>/like", methods=["POST"])
@require_default_rate_limit
def like_track(track_id):
    """Like or unlike a track."""
    from hub.services import music_controller

    data = request.get_json(silent=True) or {}
    _like = data.get("like", True)

    # Toggle the like status of the track
    is_liked = music_controller.toggle_like_track(track_id)
    return jsonify({"status": "success", "track_id": track_id, "liked": is_liked}), 200


@api_bp.route("/api/music/queue", methods=["POST"])
@require_default_rate_limit
def load_queue():
    """Load a queue for playback."""
    from hub.services import music_controller

    data = request.get_json(silent=True) or {}
    queue_id = data.get("queue_id")
    playlist_id = data.get("playlist_id")

    if queue_id:
        success = music_controller.load_queue(queue_id=queue_id)
    elif playlist_id:
        success = music_controller.load_queue(playlist_id=playlist_id)
    else:
        return jsonify({"error": "Either queue_id or playlist_id is required"}), 400

    if success:
        state = music_controller.get_playback_state()
        return jsonify(state), 200
    else:
        return jsonify({"error": "Failed to load queue"}), 400


def _resolve_music_provider(provider_id: str):
    provider = music_provider_registry.get_provider(provider_id)
    if not provider:
        return None, (jsonify({"error": f"Unknown music provider '{provider_id}'"}), 404)
    return provider, None


def _dispatch_provider_method(
    provider_id: str,
    method_name: str,
    *args,
    error_message: str = "Provider command failed.",
    result_transform=None,
    **kwargs,
):
    provider, error_response = _resolve_music_provider(provider_id)
    if error_response:
        return error_response

    method = getattr(provider, method_name, None)
    if not callable(method):
        return jsonify({"error": f"{provider.label} does not support this action."}), 400

    try:
        data = method(*args, **kwargs)
    except (MusicProviderError, spotify_auth.SpotifyAuthError) as exc:
        return jsonify({"error": str(exc)}), 400
    except NotImplementedError:
        return jsonify({"error": "Provider capability not available."}), 400
    except Exception:
        current_app.logger.exception("Music provider action failed")
        return jsonify({"error": error_message}), 500

    if result_transform:
        data = result_transform(data)

    if data is None:
        data = {"status": "ok"}

    return jsonify(data), 200


@api_bp.route("/api/music/providers", methods=["GET"])
@require_default_rate_limit
def list_music_providers():
    """Return configured music providers and the active provider."""
    providers = music_provider_registry.list_providers()
    active = music_provider_registry.get_active_provider()
    payload = {
        "providers": [provider.serialize_metadata() for provider in providers],
        "active_provider": active.id if active else None,
    }
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response, 200


@api_bp.route("/api/music/providers/active", methods=["GET"])
@require_default_rate_limit
def get_active_music_provider():
    provider = music_provider_registry.get_active_provider()
    if not provider:
        return jsonify({"active_provider": None, "providers": []}), 200
    return jsonify({"active_provider": provider.id, "provider": provider.serialize_metadata()}), 200


@api_bp.route("/api/music/providers/active", methods=["POST"])
@require_default_rate_limit
def set_active_music_provider():
    data = request.get_json(silent=True) or {} or {}
    provider_id = data.get("provider_id")
    if not provider_id:
        return jsonify({"error": "provider_id is required."}), 400
    try:
        provider = music_provider_registry.set_active_provider(provider_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"active_provider": provider.id, "provider": provider.serialize_metadata()}), 200


@api_bp.route("/api/music/providers/<provider_id>/status", methods=["GET"])
@require_default_rate_limit
def music_provider_status(provider_id):
    response, status = _dispatch_provider_method(
        provider_id,
        "get_status",
        error_message="Unable to fetch provider status.",
    )
    if status == 200:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response, status


@api_bp.route("/api/music/providers/<provider_id>/authorize", methods=["POST"])
@require_default_rate_limit
def music_provider_authorize(provider_id):
    return _dispatch_provider_method(
        provider_id, "start_authorization", error_message="Unable to start authorization flow."
    )


@api_bp.route("/api/music/providers/<provider_id>/logout", methods=["POST"])
@require_default_rate_limit
def music_provider_logout(provider_id):
    return _dispatch_provider_method(provider_id, "disconnect", error_message="Unable to disconnect provider.")


@api_bp.route("/api/music/providers/<provider_id>/play", methods=["POST"])
@require_default_rate_limit
def music_provider_play(provider_id):
    return _dispatch_provider_method(provider_id, "resume_playback")


@api_bp.route("/api/music/providers/<provider_id>/pause", methods=["POST"])
@require_default_rate_limit
def music_provider_pause(provider_id):
    return _dispatch_provider_method(provider_id, "pause_playback")


@api_bp.route("/api/music/providers/<provider_id>/next", methods=["POST"])
@require_default_rate_limit
def music_provider_next(provider_id):
    return _dispatch_provider_method(provider_id, "next_track")


@api_bp.route("/api/music/providers/<provider_id>/previous", methods=["POST"])
@require_default_rate_limit
def music_provider_previous(provider_id):
    return _dispatch_provider_method(provider_id, "previous_track")


@api_bp.route("/api/music/providers/<provider_id>/seek", methods=["POST"])
@require_default_rate_limit
def music_provider_seek(provider_id):
    data = request.get_json(silent=True) or {}
    position_ms = int(data.get("position_ms", 0))
    return _dispatch_provider_method(
        provider_id,
        "seek",
        position_ms,
        error_message="Unable to seek within the current track.",
    )


@api_bp.route("/api/music/providers/<provider_id>/playback", methods=["GET"])
@require_default_rate_limit
def music_provider_playback(provider_id):
    response, status = _dispatch_provider_method(
        provider_id,
        "get_current_playback",
        error_message="Unable to fetch playback state.",
    )
    if status == 200:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response, status


@api_bp.route("/api/music/providers/<provider_id>/queue", methods=["GET"])
@require_default_rate_limit
def music_provider_queue(provider_id):
    response, status = _dispatch_provider_method(
        provider_id,
        "get_queue",
        error_message="Unable to fetch provider queue.",
    )
    if status == 200:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response, status


@api_bp.route("/api/music/providers/<provider_id>/playlists", methods=["GET"])
@require_default_rate_limit
def music_provider_playlists(provider_id):
    try:
        limit = max(1, int(request.args.get("limit", 10)))
    except (TypeError, ValueError):
        limit = 10
    order = (request.args.get("order") or "recent").lower()
    recent_only = order in ("recent", "recently_played", "history")
    return _dispatch_provider_method(
        provider_id,
        "get_playlists",
        limit,
        recent_only=recent_only,
        error_message="Unable to load playlists.",
        result_transform=lambda data: {"items": data},
    )


@api_bp.route("/api/music/providers/<provider_id>/playlists/<playlist_id>/shuffle", methods=["POST"])
@require_default_rate_limit
def music_provider_shuffle_playlist(provider_id, playlist_id):
    data = request.get_json(silent=True) or {}
    shuffle = bool(data.get("shuffle", True))
    return _dispatch_provider_method(
        provider_id,
        "shuffle_playlist",
        playlist_id,
        shuffle=shuffle,
        error_message="Unable to start playlist.",
    )


@api_bp.route("/api/music/providers/<provider_id>/playlists/<playlist_id>/play", methods=["POST"])
@require_default_rate_limit
def music_provider_play_playlist(provider_id, playlist_id):
    """Alias for shuffle endpoint without forcing shuffle."""
    return _dispatch_provider_method(
        provider_id,
        "shuffle_playlist",
        playlist_id,
        shuffle=False,
        error_message="Unable to play playlist.",
    )


@api_bp.route("/api/music/spotify/status", methods=["GET"])
@require_default_rate_limit
def spotify_status():
    """Return the current Spotify OAuth status."""
    return music_provider_status("spotify")


@api_bp.route("/api/music/spotify/authorize", methods=["POST"])
@require_default_rate_limit
def spotify_authorize():
    """Start the Spotify OAuth flow and return the authorization URL."""
    return music_provider_authorize("spotify")


@api_bp.route("/api/music/spotify/logout", methods=["POST"])
@require_default_rate_limit
def spotify_logout():
    """Disconnect Spotify by clearing cached tokens."""
    return music_provider_logout("spotify")


@api_bp.route("/api/music/spotify/playback", methods=["GET"])
@require_default_rate_limit
def spotify_playback():
    """Return current Spotify playback information."""
    return music_provider_playback("spotify")


@api_bp.route("/api/music/spotify/queue", methods=["GET"])
@require_default_rate_limit
def spotify_queue():
    """Return the upcoming Spotify queue."""
    return music_provider_queue("spotify")


@api_bp.route("/api/music/spotify/queue/play", methods=["POST"])
@require_default_rate_limit
def spotify_queue_play_item():
    """Play a queue item immediately using its Spotify URI."""
    data = request.get_json(silent=True) or {}
    track_uri = (data.get("uri") or "").strip()
    if not track_uri:
        return jsonify({"error": "uri is required"}), 400

    return _dispatch_provider_method(
        "spotify",
        "play_queue_item",
        track_uri,
        error_message="Unable to play selected queue item.",
    )


@api_bp.route("/api/music/spotify/queue/reorder", methods=["POST"])
@require_default_rate_limit
def spotify_queue_reorder():
    """
    Reorder queue in best-effort mode.

    Spotify does not support true queue reordering; this appends selected URIs
    in the requested order.
    """
    data = request.get_json(silent=True) or {}
    uris = data.get("uris") or []
    if not isinstance(uris, list):
        return jsonify({"error": "uris must be a list"}), 400

    return _dispatch_provider_method(
        "spotify",
        "reorder_queue",
        uris,
        error_message="Unable to reorder Spotify queue.",
    )


@api_bp.route("/api/music/spotify/devices", methods=["GET"])
@require_default_rate_limit
def spotify_devices():
    """Return available Spotify Connect devices."""

    def _format_devices(data):
        devices = data if isinstance(data, list) else []
        active_id = next((device.get("id") for device in devices if device.get("is_active")), None)
        return {"devices": devices, "active_device_id": active_id}

    return _dispatch_provider_method(
        "spotify",
        "get_devices",
        error_message="Unable to load Spotify devices.",
        result_transform=_format_devices,
    )


@api_bp.route("/api/music/spotify/transfer", methods=["POST"])
@require_default_rate_limit
def spotify_transfer():
    """Transfer Spotify playback to a specific device."""
    data = request.get_json(silent=True) or {}
    device_id = (data.get("device_id") or "").strip()
    play = bool(data.get("play", True))
    if not device_id:
        return jsonify({"error": "device_id is required"}), 400

    return _dispatch_provider_method(
        "spotify",
        "transfer_playback",
        device_id,
        play=play,
        error_message="Unable to transfer Spotify playback.",
    )


@api_bp.route("/api/music/spotify/play", methods=["POST"])
@require_default_rate_limit
def spotify_play():
    """Resume Spotify playback."""
    return music_provider_play("spotify")


@api_bp.route("/api/music/spotify/pause", methods=["POST"])
@require_default_rate_limit
def spotify_pause():
    """Pause Spotify playback."""
    return music_provider_pause("spotify")


@api_bp.route("/api/music/spotify/next", methods=["POST"])
@require_default_rate_limit
def spotify_next():
    """Skip to next Spotify track."""
    return music_provider_next("spotify")


@api_bp.route("/api/music/spotify/previous", methods=["POST"])
@require_default_rate_limit
def spotify_previous():
    """Go to previous Spotify track."""
    return music_provider_previous("spotify")


@api_bp.route("/api/music/spotify/seek", methods=["POST"])
@require_default_rate_limit
def spotify_seek():
    """Seek to a position in the current Spotify track."""
    return music_provider_seek("spotify")


@api_bp.route("/api/music/spotify/playlists", methods=["GET"])
@require_default_rate_limit
def spotify_playlists():
    """Return Spotify playlists for the quick-access tray."""
    return music_provider_playlists("spotify")


@api_bp.route("/api/music/spotify/playlists/<playlist_id>/shuffle", methods=["POST"])
@require_default_rate_limit
def spotify_shuffle_playlist(playlist_id):
    """Start shuffling a Spotify playlist on the active device."""
    return music_provider_shuffle_playlist("spotify", playlist_id)


@api_bp.route("/api/admin/sports-ticker/enabled", methods=["GET"])
@require_ip_whitelist
def get_sports_ticker_enabled():
    """Get the current enabled status of the sports ticker."""
    from flask import current_app

    config = current_app.config.get("CONFIG")
    if config and hasattr(config, "features"):
        enabled = getattr(config.features, "sports_ticker_enabled", True)
    else:
        enabled = True  # Default to enabled

    return jsonify({"enabled": enabled}), 200


@api_bp.route("/api/admin/sports-ticker/enabled", methods=["PUT"])
@require_ip_whitelist
def set_sports_ticker_enabled():
    """Set the enabled status of the sports ticker."""
    import yaml
    from flask import current_app

    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled", True)

    # Update the config in memory
    config = current_app.config.get("CONFIG")
    if config and hasattr(config, "features"):
        config.features.sports_ticker_enabled = enabled

        # Update the config file on disk
        config_path = current_app.config.get("CONFIG_PATH", "config.yaml")

        # Create backup of current config
        import shutil
        from datetime import datetime

        backup_path = f"{config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(config_path, backup_path)

        # Load config as dict, update, and save
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        if config_dict is None:
            config_dict = {}

        config_dict.setdefault("features", {})["sports_ticker_enabled"] = enabled

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)

    return jsonify({"status": "success", "enabled": enabled}), 200


@api_bp.route("/api/admin/sports-ticker/mock-mode", methods=["GET"])
@require_ip_whitelist
def get_sports_ticker_mock_mode():
    """Get the current mock mode status of the sports ticker."""
    from flask import current_app

    config = current_app.config.get("CONFIG")
    if config and hasattr(config, "features"):
        mock_mode = getattr(config.features, "sports_ticker_mock_mode", False)
    else:
        mock_mode = False  # Default to disabled

    return jsonify({"mock_mode": mock_mode}), 200


@api_bp.route("/api/admin/sports-ticker/mock-mode", methods=["PUT"])
@require_ip_whitelist
def set_sports_ticker_mock_mode():
    """Set the mock mode status of the sports ticker."""
    import yaml
    from flask import current_app

    data = request.get_json(silent=True) or {}
    mock_mode = data.get("mock_mode", False)

    # Update the config in memory
    config = current_app.config.get("CONFIG")
    if config and hasattr(config, "features"):
        config.features.sports_ticker_mock_mode = mock_mode

        # Update the config file on disk
        config_path = current_app.config.get("CONFIG_PATH", "config.yaml")

        # Create backup of current config
        import shutil
        from datetime import datetime

        backup_path = f"{config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(config_path, backup_path)

        # Load config as dict, update, and save
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        if config_dict is None:
            config_dict = {}

        config_dict.setdefault("features", {})["sports_ticker_mock_mode"] = mock_mode

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)

    return jsonify({"status": "success", "mock_mode": mock_mode}), 200


@api_bp.route("/api/admin/burn-in", methods=["GET"])
@require_ip_whitelist
def get_burn_in_config():
    """Get the current burn-in mitigation settings."""
    config = current_app.config.get("CONFIG")
    config_dict = get_config_dict(config)
    burn_in = config_dict.get("ui", {}).get("burn_in", {})
    return jsonify({"burn_in": burn_in}), 200


@api_bp.route("/api/admin/burn-in", methods=["PUT"])
@require_ip_whitelist
def set_burn_in_config():
    """Update burn-in mitigation settings."""
    import yaml

    def _clamp_int(value, min_value, max_value, default):
        try:
            value = int(value)
        except (TypeError, ValueError):
            return default
        return max(min_value, min(max_value, value))

    def _clamp_float(value, min_value, max_value, default):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return default
        return max(min_value, min(max_value, value))

    data = request.get_json(silent=True) or {}
    updates = {}

    if "enabled" in data:
        updates["enabled"] = bool(data.get("enabled"))
    if "shift_enabled" in data:
        updates["shift_enabled"] = bool(data.get("shift_enabled"))
    if "dim_enabled" in data:
        updates["dim_enabled"] = bool(data.get("dim_enabled"))

    if "shift_interval_seconds" in data:
        updates["shift_interval_seconds"] = _clamp_int(data.get("shift_interval_seconds"), 30, 1800, 180)
    if "shift_range_px" in data:
        updates["shift_range_px"] = _clamp_int(data.get("shift_range_px"), 4, 40, 12)
    if "dim_idle_seconds" in data:
        updates["dim_idle_seconds"] = _clamp_int(data.get("dim_idle_seconds"), 30, 3600, 300)
    if "dim_level" in data:
        updates["dim_level"] = _clamp_float(data.get("dim_level"), 0.3, 1.0, 0.6)

    config = current_app.config.get("CONFIG")
    if config and hasattr(config, "ui") and hasattr(config.ui, "burn_in"):
        for key, value in updates.items():
            setattr(config.ui.burn_in, key, value)

        config_path = current_app.config.get("CONFIG_PATH", "config.yaml")

        import shutil
        from datetime import datetime

        backup_path = f"{config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(config_path, backup_path)

        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        if config_dict is None:
            config_dict = {}

        ui_config = config_dict.setdefault("ui", {})
        burn_in_config = ui_config.setdefault("burn_in", {})
        burn_in_config.update(updates)

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)

    burn_in = get_config_dict(config).get("ui", {}).get("burn_in", {})
    return jsonify({"status": "success", "burn_in": burn_in}), 200


@api_bp.route("/api/chores", methods=["GET"])
@require_default_rate_limit
def get_all_chores():
    """Get all chores with optional filtering."""
    from hub.services import chore_service

    assignee = request.args.get("assignee")
    completed = request.args.get("completed")

    # Convert 'completed' parameter to boolean
    completed_bool = None
    if completed is not None:
        completed_bool = completed.lower() in ["true", "1", "yes", "on"]

    chores = chore_service.get_chores(assignee=assignee, completed=completed_bool)
    return jsonify([chore.to_dict() for chore in chores])


@api_bp.route("/api/chores", methods=["POST"])
@require_default_rate_limit
def create_chore():
    """Create a new chore."""
    from hub.services import chore_service

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    assignee = data.get("assignee", "").strip()
    due_date_str = data.get("due_date")
    recurring_schedule = data.get("recurring_schedule")
    priority = data.get("priority", "normal")
    description = data.get("description", "").strip()

    # Parse due_date if provided
    due_date = None
    if due_date_str:
        try:
            from datetime import datetime

            due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "Invalid due_date format"}), 400

    chore = chore_service.create_chore(
        title=title,
        assignee=assignee,
        due_date=due_date,
        recurring_schedule=recurring_schedule,
        priority=priority,
        description=description,
    )

    if chore:
        return jsonify(chore.to_dict()), 201
    else:
        return jsonify({"error": "Failed to create chore"}), 500


@api_bp.route("/api/chores/<int:id>", methods=["GET"])
@require_default_rate_limit
def get_chore(id):
    """Get a specific chore by ID."""
    from hub.services import chore_service

    chore = chore_service.get_chore(id)
    if not chore:
        return jsonify({"error": "Chore not found"}), 404
    return jsonify(chore.to_dict()), 200


@api_bp.route("/api/chores/<int:id>", methods=["PUT"])
@require_admin_rate_limit
def update_chore(id):
    """Update a chore."""
    from hub.services import chore_service

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    chore = chore_service.update_chore(
        chore_id=id,
        title=data.get("title"),
        assignee=data.get("assignee"),
        due_date=data.get("due_date"),
        completed=data.get("completed"),
        recurring_schedule=data.get("recurring_schedule"),
        priority=data.get("priority"),
        description=data.get("description"),
    )

    if chore:
        return jsonify(chore.to_dict()), 200
    else:
        return jsonify({"error": "Chore not found"}), 404


@api_bp.route("/api/chores/<int:id>", methods=["DELETE"])
@require_admin_rate_limit
def delete_chore(id):
    """Delete a chore."""
    from hub.services import chore_service

    success = chore_service.delete_chore(id)
    if success:
        return jsonify({"status": "deleted"}), 200
    else:
        return jsonify({"error": "Chore not found"}), 404


@api_bp.route("/api/chores/<int:id>/complete", methods=["POST"])
@require_default_rate_limit
def complete_chore(id):
    """Mark a chore as completed."""
    from hub.services import chore_service

    chore = chore_service.complete_chore(id)
    if chore:
        return jsonify(chore.to_dict()), 200
    else:
        return jsonify({"error": "Chore not found"}), 404


@api_bp.route("/api/chores/<int:id>/uncomplete", methods=["POST"])
@require_default_rate_limit
def uncomplete_chore(id):
    """Mark a chore as incomplete."""
    from hub.services import chore_service

    chore = chore_service.uncomplete_chore(id)
    if chore:
        return jsonify(chore.to_dict()), 200
    else:
        return jsonify({"error": "Chore not found"}), 404


@api_bp.route("/api/chores/due-soon", methods=["GET"])
@require_default_rate_limit
def get_chores_due_soon():
    """Get chores that are due soon."""
    from hub.services import chore_service

    days = int(request.args.get("days", 7))  # Default to 7 days
    chores = chore_service.get_chores_due_soon(days=days)
    return jsonify([chore.to_dict() for chore in chores])


@api_bp.route("/api/chores/overdue", methods=["GET"])
@require_default_rate_limit
def get_overdue_chores():
    """Get overdue chores."""
    from hub.services import chore_service

    chores = chore_service.get_overdue_chores()
    return jsonify([chore.to_dict() for chore in chores])


@api_bp.route("/api/admin/sports-ticker/refresh", methods=["POST"])
@require_ip_whitelist
def admin_refresh_sports_ticker_data():
    """Admin endpoint to manually refresh sports ticker data."""
    from hub.services import sports_ticker_service

    success = sports_ticker_service.refresh_sports_ticker_data()
    if success:
        return jsonify({"status": "success", "message": "Sports ticker data refreshed successfully"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to refresh sports ticker data"}), 500


@api_bp.route("/api/admin/clear-cache", methods=["POST"])
@require_ip_whitelist
def clear_application_caches():
    """Admin endpoint to clear various application caches."""
    import os

    from hub.cache import clear_cache, clear_calendar_cache, clear_sports_cache, clear_weather_cache
    from hub.services.sports_ticker_service import _get_cache_file_path

    data = request.get_json(silent=True) or {}
    cache_types = data.get("cache_types", ["weather", "calendar", "sports", "ticker"])

    results = {}

    if "weather" in cache_types:
        try:
            cleared_count = clear_weather_cache()
            results["weather"] = {"status": "success", "cleared_items": cleared_count}
        except Exception as e:
            results["weather"] = {"status": "error", "message": str(e)}

    if "calendar" in cache_types:
        try:
            cleared_count = clear_calendar_cache()
            results["calendar"] = {"status": "success", "cleared_items": cleared_count}
        except Exception as e:
            results["calendar"] = {"status": "error", "message": str(e)}

    if "sports" in cache_types:
        try:
            cleared_count = clear_sports_cache()
            results["sports"] = {"status": "success", "cleared_items": cleared_count}
        except Exception as e:
            results["sports"] = {"status": "error", "message": str(e)}

    if "ticker" in cache_types:
        try:
            ticker_cache_path = _get_cache_file_path()
            if os.path.exists(ticker_cache_path):
                os.remove(ticker_cache_path)
                results["ticker"] = {"status": "success", "message": "Ticker cache file deleted"}
            else:
                results["ticker"] = {"status": "success", "message": "Ticker cache file did not exist"}
        except Exception as e:
            results["ticker"] = {"status": "error", "message": str(e)}

    # Also clear general cache if it exists
    if "general" in cache_types:
        try:
            cleared_count = clear_cache()
            results["general"] = {"status": "success", "cleared_items": cleared_count}
        except Exception as e:
            results["general"] = {"status": "error", "message": str(e)}

    return jsonify({"status": "success", "results": results}), 200


@api_bp.route("/api/admin/restart-app", methods=["POST"])
@require_ip_whitelist
def restart_application():
    """Admin endpoint to restart the application (for memory management)."""

    try:
        # In a web server context, we typically can't restart the process directly
        # Instead, we return a message indicating the request was received
        # The actual restart should be handled by a process supervisor (systemd, etc.)

        # Option 1: Return message for external restart
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Restart requested. Please restart the application manually or through your process manager.",
                    "needs_external_restart": True,
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
