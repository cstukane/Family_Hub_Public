import os

from flask import jsonify, request

from hub.plugins.manager import plugin_manager
from hub.plugins.marketplace import PluginMarketplace
from hub.utils.decorators import require_ip_whitelist

from . import api_bp


def _safe_extract_zip(zip_ref, target_dir: str) -> None:
    """Safely extract a ZIP archive, preventing zip-slip."""
    abs_target = os.path.abspath(target_dir)
    for member in zip_ref.namelist():
        member_path = os.path.abspath(os.path.join(abs_target, member))
        if not member_path.startswith(abs_target + os.sep) and member_path != abs_target:
            raise ValueError(f"Unsafe zip entry: {member}")
    zip_ref.extractall(abs_target)


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
