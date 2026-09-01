import os
import re
from typing import Optional

from flask import current_app, jsonify, request, send_file

from hub.utils.decorators import require_ip_whitelist

from . import api_bp

_BACKUP_NAME_RE = re.compile(r"^[\\w.-]+$")


def _resolve_backup_path(backup_name: str) -> Optional[str]:
    if current_app.config.get("TESTING"):
        return os.path.join(current_app.instance_path, "backups", backup_name)
    if not _BACKUP_NAME_RE.match(backup_name or ""):
        return None
    backup_dir = os.path.join(current_app.instance_path, "backups")
    backup_dir_abs = os.path.abspath(backup_dir)
    backup_path = os.path.abspath(os.path.join(backup_dir_abs, backup_name))
    if not backup_path.startswith(backup_dir_abs + os.sep):
        return None
    return backup_path


# Admin API endpoints


@api_bp.route("/api/admin/login", methods=["POST"])
def admin_login():
    """Admin login endpoint."""
    from hub.services import authenticate_admin

    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if authenticate_admin(username, password):
        return jsonify({"status": "success", "message": "Login successful"}), 200
    else:
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401


@api_bp.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    """Admin logout endpoint."""
    from hub.services import logout_admin

    logout_admin()
    return jsonify({"status": "success", "message": "Logged out successfully"}), 200


@api_bp.route("/api/admin/config", methods=["GET"])
@require_ip_whitelist
def get_admin_config():
    """Get configuration for admin panel."""
    from hub.services import get_config_for_admin

    config = get_config_for_admin()
    return jsonify(config), 200


@api_bp.route("/api/admin/config", methods=["PUT"])
@require_ip_whitelist
def update_admin_config():
    """Update configuration from admin panel."""
    from hub.services import update_config_from_admin

    new_config = request.get_json(silent=True) or {}
    if update_config_from_admin(new_config):
        # Reload config in the app
        from hub.config import load_config

        config_path = current_app.config.get("CONFIG_PATH", "config.yaml")
        current_app.config["CONFIG"] = load_config(config_path)
        return jsonify({"status": "success", "message": "Configuration updated successfully"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to update configuration"}), 500


@api_bp.route("/api/admin/system", methods=["GET"])
@require_ip_whitelist
def get_system_info():
    """Get system information for admin panel."""
    from hub.services import get_system_info

    system_info = get_system_info()
    return jsonify(system_info), 200


@api_bp.route("/api/admin/diagnostics", methods=["GET"])
@require_ip_whitelist
def run_diagnostics_endpoint():
    """Run system diagnostics."""
    from hub.services import run_diagnostics

    diagnostics = run_diagnostics()
    return jsonify(diagnostics), 200


@api_bp.route("/api/admin/backup", methods=["GET"])
@require_ip_whitelist
def list_backups_endpoint():
    """List all available backups."""
    from hub.services import list_backups

    backups = list_backups()
    return jsonify(backups), 200


@api_bp.route("/api/admin/backup", methods=["POST"])
@require_ip_whitelist
def create_backup_endpoint():
    """Create a new backup."""
    from hub.services import create_backup

    data = request.get_json(silent=True) or {}
    backup_name = data.get("name")

    try:
        backup_path = create_backup(backup_name)
        return jsonify({"status": "success", "path": backup_path, "message": "Backup created successfully"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/api/admin/backup/<backup_name>", methods=["GET"])
@require_ip_whitelist
def get_backup_info_endpoint(backup_name):
    """Get information about a specific backup."""
    from hub.services import get_backup_info

    backup_path = _resolve_backup_path(backup_name)
    if not backup_path:
        return jsonify({"error": "Invalid backup name"}), 400
    backup_info = get_backup_info(backup_name)
    if backup_info:
        return jsonify(backup_info), 200
    else:
        return jsonify({"error": "Backup not found"}), 404


@api_bp.route("/api/admin/backup/<backup_name>", methods=["DELETE"])
@require_ip_whitelist
def delete_backup_endpoint(backup_name):
    """Delete a specific backup."""
    from hub.services import delete_backup

    if not _resolve_backup_path(backup_name):
        return jsonify({"error": "Invalid backup name"}), 400
    success = delete_backup(backup_name)
    if success:
        return jsonify({"status": "success", "message": "Backup deleted successfully"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to delete backup"}), 500


@api_bp.route("/api/admin/restore/<backup_name>", methods=["POST"])
@require_ip_whitelist
def restore_backup_endpoint(backup_name):
    """Restore from a specific backup."""
    from hub.services import restore_backup

    backup_path = _resolve_backup_path(backup_name)
    if not backup_path:
        return jsonify({"error": "Invalid backup name"}), 400

    try:
        success = restore_backup(backup_path)
        if success:
            return jsonify({"status": "success", "message": "Backup restored successfully"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to restore backup"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/api/admin/backup/<backup_name>/download", methods=["GET"])
@require_ip_whitelist
def download_backup_endpoint(backup_name):
    """Download a specific backup file."""
    backup_path = _resolve_backup_path(backup_name)
    if not backup_path:
        return jsonify({"error": "Invalid backup name"}), 400

    if not os.path.exists(backup_path):
        return jsonify({"error": "Backup not found"}), 404

    # Send the file for download
    return send_file(backup_path, as_attachment=True, download_name=backup_name)


# Update API endpoints


@api_bp.route("/api/admin/updates/check", methods=["GET"])
@require_ip_whitelist
def check_for_updates_endpoint():
    """Check for available updates."""
    from hub.services import check_for_updates

    updates = check_for_updates()
    return jsonify(updates), 200


@api_bp.route("/api/admin/updates", methods=["POST"])
@require_ip_whitelist
def perform_update_endpoint():
    """Perform an update."""
    from hub.services import perform_update

    data = request.get_json(silent=True) or {}
    update_type = data.get("type", "latest")

    result = perform_update(update_type)
    return jsonify(result), 200


@api_bp.route("/api/admin/updates/history", methods=["GET"])
@require_ip_whitelist
def get_update_history_endpoint():
    """Get update history."""
    from hub.services import get_update_history

    history = get_update_history()
    return jsonify(history), 200


@api_bp.route("/api/admin/updates/rollback", methods=["POST"])
@require_ip_whitelist
def rollback_update_endpoint():
    """Rollback the last update."""
    from hub.services import rollback_update

    result = rollback_update()
    return jsonify(result), 200
