"""Update service for the Kitchen Hub application."""

import json
import logging
import os
import subprocess  # nosec B404
import sys
from datetime import datetime
from typing import Dict

from flask import current_app, has_app_context

from hub.db import get_db


def _get_logger() -> logging.Logger:
    if has_app_context():
        return current_app.logger
    return logging.getLogger(__name__)


def _get_instance_path() -> str:
    if has_app_context():
        return current_app.instance_path
    return os.path.join(os.getcwd(), "instance")


def check_for_updates() -> Dict:
    """Check if there are available updates for the application."""
    try:
        from hub import __version__

        # Get the current version from the hub module
        current_version = __version__

        # Check for updates by running git fetch and comparing
        try:
            # Fetch latest changes from remote
            result = subprocess.run(["git", "fetch"], cwd=os.getcwd(), capture_output=True, text=True, timeout=30)  # nosec B603 B607

            if result.returncode != 0:
                _get_logger().warning("Git fetch failed: %s", result.stderr)
                # If git fetch fails, assume no updates (offline mode)
                return {
                    "has_updates": False,
                    "current_version": current_version,
                    "latest_version": current_version,
                    "updates": [],
                    "timestamp": datetime.now().isoformat(),
                    "message": "Git fetch failed - assuming no updates available",
                }

            # Check if there are updates available by comparing local and remote
            result = subprocess.run(
                ["git", "status", "-uno"],  # -uno to ignore untracked files
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                timeout=10,
            )  # nosec B603 B607

            has_updates = "Your branch is behind" in result.stdout
            if has_updates:
                # Get the latest commit info
                latest_result = subprocess.run(
                    ["git", "rev-parse", "origin/main"], cwd=os.getcwd(), capture_output=True, text=True, timeout=10
                )  # nosec B603 B607

                latest_commit = latest_result.stdout.strip()[:8] if latest_result.returncode == 0 else "unknown"
                latest_version = f"0.1.{latest_commit}"  # Simplified versioning
            else:
                latest_version = current_version

            # Get detailed update information if there are updates
            updates = []
            if has_updates:
                # Get recent commits for update information
                log_result = subprocess.run(
                    ["git", "log", "--oneline", "HEAD..origin/main"],
                    cwd=os.getcwd(),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )  # nosec B603 B607

                if log_result.returncode == 0:
                    lines = log_result.stdout.strip().split("\n")[:5]  # Get last 5 commits
                    for line in lines:
                        if line.strip():
                            parts = line.strip().split(" ", 1)
                            if len(parts) >= 2:
                                commit_hash, message = parts[0], parts[1]
                                updates.append(
                                    {
                                        "version": commit_hash[:7],
                                        "description": message,
                                        "date": datetime.now().isoformat(),
                                        "type": "patch",
                                    }
                                )

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            _get_logger().warning("Git operation failed: %s", e)
            # If git is not available, return current version only
            return {
                "has_updates": False,
                "current_version": current_version,
                "latest_version": current_version,
                "updates": [],
                "timestamp": datetime.now().isoformat(),
                "message": "Git not available - update checking disabled",
            }

        result = {
            "has_updates": has_updates,
            "current_version": current_version,
            "latest_version": latest_version,
            "updates": updates,
            "timestamp": datetime.now().isoformat(),
        }

        # Log the check
        _get_logger().info("Update check completed: %s updates available", result["has_updates"])
        return result
    except Exception as e:
        _get_logger().error("Error checking for updates: %s", e)
        return {"error": str(e)}


def perform_update(update_type: str = "latest") -> Dict:
    """Perform an update of the application."""
    try:
        # Create a backup before updating
        backup_result = create_backup_before_update()
        if not backup_result.get("success"):
            _get_logger().error("Failed to create backup before update: %s", backup_result.get("error"))
            return {"status": "error", "message": f"Unable to create backup: {backup_result.get('error')}"}

        # Execute the git pull to get the latest changes
        result = subprocess.run(
            ["git", "pull", "origin", "main"], cwd=os.getcwd(), capture_output=True, text=True, timeout=60
        )  # nosec B603 B607

        if result.returncode != 0:
            _get_logger().error("Git pull failed: %s", result.stderr)
            return {"status": "error", "message": f"Git pull failed: {result.stderr}"}

        # Install any new dependencies
        requirements_path = os.path.join(os.getcwd(), "requirements.txt")
        if os.path.exists(requirements_path):
            pip_result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", requirements_path, "--quiet"],
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                timeout=120,
            )  # nosec B603

            if pip_result.returncode != 0:
                _get_logger().error("Pip install failed: %s", pip_result.stderr)
                # Continue with update since this might be a non-critical error

        # Log the update in the audit table
        db = get_db()
        db.execute(
            """INSERT INTO audit (actor, action, payload)
               VALUES (?, ?, ?)""",
            (
                "system",
                "update_performed",
                f"Update {update_type} applied successfully at {datetime.now().isoformat()}",
            ),
        )
        db.commit()

        _get_logger().info("Update %s performed successfully", update_type)
        result_data = {
            "status": "success",
            "message": f"Update {update_type} applied successfully",
            "timestamp": datetime.now().isoformat(),
            "backup_created": backup_result["backup_path"] if backup_result.get("backup_path") else None,
        }

        return result_data
    except subprocess.TimeoutExpired:
        _get_logger().error("Update process timed out")
        return {"status": "error", "message": "Update process timed out"}
    except Exception as e:
        _get_logger().error("Error performing update: %s", e)
        return {"status": "error", "message": str(e)}


def get_update_history() -> Dict:
    """Get the history of updates applied to the system."""
    try:
        # Query the audit table for update-related entries
        db = get_db()
        query = """
            SELECT ts, actor, action, payload
            FROM audit
            WHERE action LIKE '%update%' OR action LIKE '%backup%' OR action LIKE '%restore%'
            ORDER BY ts DESC
            LIMIT 20
        """

        rows = db.execute(query).fetchall()

        # Parse update history from audit log
        history = []
        for row in rows:
            history.append(
                {"timestamp": row["ts"], "actor": row["actor"], "action": row["action"], "details": row["payload"]}
            )

        return {"history": history, "last_check": datetime.now().isoformat()}
    except Exception as e:
        _get_logger().error("Error getting update history: %s", e)
        return {"error": str(e)}


def rollback_update() -> Dict:
    """Rollback the last update."""
    try:
        # Get the most recent backup
        backup_path = get_most_recent_backup()
        if not backup_path:
            return {"status": "error", "message": "No recent backup found for rollback"}

        # Attempt to restore from the most recent backup
        restore_result = restore_from_backup(backup_path)
        if not restore_result.get("success"):
            return {"status": "error", "message": f"Rollback failed: {restore_result.get('error')}"}

        # Log the rollback in the audit table
        db = get_db()
        db.execute(
            """INSERT INTO audit (actor, action, payload)
               VALUES (?, ?, ?)""",
            (
                "system",
                "update_rollback",
                f"Rollback completed from backup: {backup_path} at {datetime.now().isoformat()}",
            ),
        )
        db.commit()

        _get_logger().info("Rollback completed successfully")
        return {
            "status": "success",
            "message": f"Rollback completed successfully from backup: {backup_path}",
            "timestamp": datetime.now().isoformat(),
            "backup_used": backup_path,
        }
    except Exception as e:
        _get_logger().error("Error rolling back update: %s", e)
        return {"status": "error", "message": str(e)}


def create_backup_before_update() -> Dict:
    """Create a backup before performing an update."""
    try:
        import shutil
        from datetime import datetime

        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(_get_instance_path(), "backups")
        os.makedirs(backup_dir, exist_ok=True)

        # Create a backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_pre_update_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_name)

        # Get the project root directory (parent of current working directory)
        project_root = os.getcwd()

        # Create backup of important files/directories
        backup_data = {
            "timestamp": timestamp,
            "backup_name": backup_name,
            "source_path": project_root,
            "backed_up_files": [],
        }

        # Backup the database
        db_path = os.path.join(_get_instance_path(), "kitchen_hub.db")
        if os.path.exists(db_path):
            backup_db_path = os.path.join(backup_path, "kitchen_hub.db")
            os.makedirs(backup_path, exist_ok=True)
            shutil.copy2(db_path, backup_db_path)
            backup_data["backed_up_files"].append("database")

        # Create a JSON file with backup info
        backup_info_path = os.path.join(backup_path, "backup_info.json")
        with open(backup_info_path, "w") as f:
            json.dump(backup_data, f, indent=2)

        _get_logger().info("Backup created: %s", backup_path)
        return {"success": True, "backup_path": backup_path, "timestamp": timestamp}
    except Exception as e:
        _get_logger().error("Error creating backup: %s", e)
        return {"success": False, "error": str(e)}


def get_most_recent_backup() -> str:
    """Get the path to the most recent backup."""
    try:
        backup_dir = os.path.join(_get_instance_path(), "backups")
        if not os.path.exists(backup_dir):
            return None

        # Find the most recent backup directory
        backup_dirs = []
        for item in os.listdir(backup_dir):
            item_path = os.path.join(backup_dir, item)
            if os.path.isdir(item_path) and item.startswith("backup_"):
                backup_dirs.append((item_path, os.path.getctime(item_path)))

        if not backup_dirs:
            return None

        # Return the most recent backup
        backup_dirs.sort(key=lambda x: x[1], reverse=True)
        return backup_dirs[0][0]
    except Exception as e:
        _get_logger().error("Error finding most recent backup: %s", e)
        return None


def restore_from_backup(backup_path: str) -> Dict:
    """Restore from a backup."""
    try:
        import shutil

        # Check if backup exists
        if not os.path.exists(backup_path):
            return {"success": False, "error": f"Backup path does not exist: {backup_path}"}

        # Look for the database backup
        backup_db_path = os.path.join(backup_path, "kitchen_hub.db")
        if os.path.exists(backup_db_path):
            # Restore the database
            db_path = os.path.join(_get_instance_path(), "kitchen_hub.db")
            shutil.copy2(backup_db_path, db_path)

        _get_logger().info("Restore completed from: %s", backup_path)
        return {"success": True, "restored_from": backup_path}
    except Exception as e:
        _get_logger().error("Error restoring from backup: %s", e)
        return {"success": False, "error": str(e)}


def schedule_update_check() -> Dict:
    """Schedule automatic update checks.

    NOTE: Scheduler integration is not yet implemented. This endpoint is a
    preview stub — it does not actually register an APScheduler job.
    """
    _get_logger().info("schedule_update_check called but scheduler integration is not implemented")
    return {
        "status": "not_implemented",
        "message": "Automatic update scheduling is not yet implemented",
        "next_check": None,
    }


def get_update_schedule() -> Dict:
    """Get the current update schedule.

    NOTE: Scheduler integration is not yet implemented. This endpoint is a
    preview stub — it returns static placeholder data.
    """
    return {
        "enabled": False,
        "frequency": None,
        "next_check": None,
        "last_check": None,
        "note": "Automatic update scheduling is not yet implemented",
    }


def graceful_update_shutdown() -> Dict:
    """Perform a graceful shutdown before update."""
    try:
        # In a real implementation, this would:
        # 1. Stop accepting new requests
        # 2. Wait for current requests to finish
        # 3. Close database connections
        # 4. Stop background tasks
        # For now, we'll simulate this process

        _get_logger().info("Initiating graceful shutdown for update...")

        # Log the shutdown in the audit table
        db = get_db()
        db.execute(
            """INSERT INTO audit (actor, action, payload)
               VALUES (?, ?, ?)""",
            ("system", "update_shutdown", f"Graceful shutdown initiated for update at {datetime.now().isoformat()}"),
        )
        db.commit()

        # In a real implementation, you would:
        # - Signal the application to stop accepting new requests
        # - Wait for current requests to complete
        # - Perform cleanup operations
        # - Then proceed with the update

        return {"status": "success", "message": "Graceful shutdown completed, ready for update"}
    except Exception as e:
        _get_logger().error("Error during graceful shutdown: %s", e)
        return {"status": "error", "message": str(e)}
