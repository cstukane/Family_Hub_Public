"""Backup and restore service for the Family Hub application."""

import os
import shutil
import tarfile
from datetime import datetime
from typing import Dict, List

from flask import current_app

from hub.utils.runtime import get_runtime_root


def _safe_extract_tar(tar: tarfile.TarFile, target_dir: str) -> None:
    """Safely extract a tar archive, preventing tar-slip."""
    abs_target = os.path.abspath(target_dir)
    safe_members = []
    for member in tar.getmembers():
        member_path = os.path.abspath(os.path.join(abs_target, member.name))
        if not member_path.startswith(abs_target + os.sep) and member_path != abs_target:
            raise ValueError(f"Unsafe tar entry: {member.name}")
        safe_members.append(member)
    tar.extractall(abs_target, members=safe_members)  # nosec B202


def create_backup(backup_name: str = None) -> str:
    """Create a backup of the application data.

    Creates a backup containing:
    - Database file
    - Configuration file
    - Instance folder contents (tokens, etc.)
    """
    try:
        if not backup_name:
            backup_name = f"kitchen_hub_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"

        runtime_root = get_runtime_root()
        backup_dir = os.path.join(runtime_root, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        backup_path = os.path.join(backup_dir, backup_name)

        # Get the paths to backup
        db_path = current_app.config.get("DATABASE")
        config_path = current_app.config.get("CONFIG_PATH", "config.yaml")
        instance_dir = runtime_root

        with tarfile.open(backup_path, "w:gz") as tar:
            # Add database file
            if os.path.exists(db_path):
                tar.add(db_path, arcname=os.path.basename(db_path))

            # Add config file
            if os.path.exists(config_path):
                tar.add(config_path, arcname=os.path.basename(config_path))

            # Add instance directory (excluding backups subdirectory to avoid recursion)
            if os.path.exists(instance_dir):
                for item in os.listdir(instance_dir):
                    item_path = os.path.join(instance_dir, item)
                    if item != "backups" and os.path.isfile(item_path):
                        tar.add(item_path, arcname=f"instance/{item}")
                    elif item != "backups" and os.path.isdir(item_path):
                        # Add directories but skip backups
                        tar.add(item_path, arcname=f"instance/{item}")

        current_app.logger.info(f"Backup created successfully: {backup_path}")
        return backup_path
    except Exception as e:
        current_app.logger.error(f"Error creating backup: {e}")
        raise


def list_backups() -> List[Dict[str, str]]:
    """List all available backups."""
    backup_dir = os.path.join(get_runtime_root(), "backups")

    if not os.path.exists(backup_dir):
        return []

    backups = []
    for filename in os.listdir(backup_dir):
        if filename.endswith(".tar.gz"):
            filepath = os.path.join(backup_dir, filename)
            stat = os.stat(filepath)
            backups.append(
                {
                    "name": filename,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": filepath,
                }
            )

    # Sort by modification time, newest first
    backups.sort(key=lambda x: x["modified"], reverse=True)
    return backups


def restore_backup(backup_path: str) -> bool:
    """Restore application data from a backup.

    Restores:
    - Database file
    - Configuration file
    - Instance folder contents
    """
    try:
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Stop the scheduler during restore if it exists
        scheduler_running = False
        if hasattr(current_app, "scheduler"):
            scheduler_running = current_app.scheduler.running
            if scheduler_running:
                current_app.scheduler.shutdown()

        # Extract the backup to a temporary directory first
        runtime_root = get_runtime_root()
        temp_dir = os.path.join(runtime_root, "temp_restore")
        os.makedirs(temp_dir, exist_ok=True)

        with tarfile.open(backup_path, "r:gz") as tar:
            _safe_extract_tar(tar, temp_dir)

        # Get the paths to restore to
        db_path = current_app.config.get("DATABASE")
        config_path = current_app.config.get("CONFIG_PATH", "config.yaml")
        instance_dir = runtime_root

        # Restore database
        extracted_db_files = [f for f in os.listdir(temp_dir) if f.endswith(".db")]
        if extracted_db_files:
            # If there's a db file in the root of the archive, use it
            src_db = os.path.join(temp_dir, extracted_db_files[0])
            if os.path.exists(src_db):
                shutil.copy2(src_db, db_path)

        # Restore config
        extracted_config_files = [f for f in os.listdir(temp_dir) if f.endswith(".yaml") or f.endswith(".yml")]
        if extracted_config_files:
            src_config = os.path.join(temp_dir, extracted_config_files[0])
            if os.path.exists(src_config):
                # Backup existing config before restoring
                if os.path.exists(config_path):
                    backup_config = f"{config_path}.restore_backup"
                    shutil.copy2(config_path, backup_config)
                shutil.copy2(src_config, config_path)

        # Restore instance folder contents (excluding the backups directory which should remain)
        extracted_instance_dir = os.path.join(temp_dir, "instance")
        if os.path.exists(extracted_instance_dir):
            for item in os.listdir(extracted_instance_dir):
                src_item = os.path.join(extracted_instance_dir, item)
                dst_item = os.path.join(instance_dir, item)

                if os.path.isfile(src_item):
                    shutil.copy2(src_item, dst_item)
                elif os.path.isdir(src_item):
                    if os.path.exists(dst_item):
                        shutil.rmtree(dst_item)
                    shutil.copytree(src_item, dst_item)

        # Clean up temp directory
        shutil.rmtree(temp_dir)

        current_app.logger.info(f"Backup restored successfully from: {backup_path}")

        # Restart scheduler if it was running
        if scheduler_running and hasattr(current_app, "create_scheduler"):
            current_app.scheduler = current_app.create_scheduler(current_app)

        return True
    except Exception as e:
        current_app.logger.error(f"Error restoring backup: {e}")
        raise


def delete_backup(backup_name: str) -> bool:
    """Delete a specific backup file."""
    try:
        backup_dir = os.path.join(get_runtime_root(), "backups")
        backup_path = os.path.join(backup_dir, backup_name)

        if os.path.exists(backup_path):
            os.remove(backup_path)
            current_app.logger.info(f"Backup deleted: {backup_path}")
            return True
        else:
            current_app.logger.warning(f"Backup not found for deletion: {backup_path}")
            return False
    except Exception as e:
        current_app.logger.error(f"Error deleting backup: {e}")
        raise


def get_backup_info(backup_name: str) -> Dict:
    """Get information about a specific backup."""
    try:
        backup_dir = os.path.join(get_runtime_root(), "backups")
        backup_path = os.path.join(backup_dir, backup_name)

        if not os.path.exists(backup_path):
            return None

        stat = os.stat(backup_path)

        # Try to get contents info without extracting
        contents = []
        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                for member in tar.getmembers():
                    contents.append(
                        {"name": member.name, "size": member.size, "type": "directory" if member.isdir() else "file"}
                    )
        except Exception:
            contents = [{"name": "Error reading contents", "size": 0, "type": "error"}]

        return {
            "name": backup_name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "path": backup_path,
            "contents": contents,
        }
    except Exception as e:
        current_app.logger.error(f"Error getting backup info: {e}")
        return None
