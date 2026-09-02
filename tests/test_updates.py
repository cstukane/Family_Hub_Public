"""Tests for the update functionality added in Phase 17."""

import json
import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from hub.config import load_config
from hub.services import update


def test_check_for_updates():
    """Test the check_for_updates function."""
    with patch("subprocess.run") as mock_run:
        # Mock the git fetch response
        mock_fetch_result = MagicMock()
        mock_fetch_result.returncode = 0
        mock_fetch_result.stdout = ""
        mock_fetch_result.stderr = ""

        # Mock the git status response
        mock_status_result = MagicMock()
        mock_status_result.returncode = 0
        mock_status_result.stdout = "Your branch is behind 'origin/main' by 1 commit."

        # Mock the git log response
        mock_log_result = MagicMock()
        mock_log_result.returncode = 0
        mock_log_result.stdout = "abc1234 Update README\nxyz5678 Fix bug"

        # Create a side effect that returns different results for different commands
        def run_side_effect(args, **kwargs):
            if args == ["git", "fetch"]:
                return mock_fetch_result
            elif "status" in args:
                return mock_status_result
            elif "log" in args:
                return mock_log_result
            else:
                # Default return for other commands
                result = MagicMock()
                result.returncode = 0
                result.stdout = "abc1234"
                return result

        mock_run.side_effect = run_side_effect

        result = update.check_for_updates()

        assert "has_updates" in result
        assert "current_version" in result
        assert "latest_version" in result
        assert "updates" in result
        assert "timestamp" in result


def test_perform_update():
    """Test the perform_update function."""
    with patch("subprocess.run") as mock_run:
        with patch("sys.executable", "/usr/bin/python3"):
            # Mock successful git pull
            mock_pull_result = MagicMock()
            mock_pull_result.returncode = 0
            mock_pull_result.stdout = "Already up to date."

            # Mock successful pip install
            mock_pip_result = MagicMock()
            mock_pip_result.returncode = 0
            mock_pip_result.stdout = "Successfully installed"

            def run_side_effect(args, **kwargs):
                if "pull" in args:
                    return mock_pull_result
                elif "pip" in args:
                    return mock_pip_result
                else:
                    result = MagicMock()
                    result.returncode = 0
                    result.stdout = "test"
                    return result

            mock_run.side_effect = run_side_effect

            # Mock the get_db function
            with patch("hub.services.update.get_db") as mock_get_db:
                mock_db = MagicMock()
                mock_get_db.return_value = mock_db
                mock_db.execute.return_value = mock_db
                mock_db.commit.return_value = None

                result = update.perform_update()

                assert result["status"] == "success"
                assert "Update latest applied successfully" in result["message"]
                assert "timestamp" in result


def test_get_update_history():
    """Test the get_update_history function."""
    with patch("hub.services.update.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock query results
        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda key: {
            "ts": datetime.now().isoformat(),
            "actor": "system",
            "action": "update_performed",
            "payload": "Update applied successfully",
        }[key]

        mock_db.execute.return_value.fetchall.return_value = [mock_row]

        result = update.get_update_history()

        assert "history" in result
        assert "last_check" in result
        assert isinstance(result["history"], list)


def test_rollback_update():
    """Test the rollback_update function."""
    with patch("hub.services.update.get_most_recent_backup") as mock_get_backup:
        mock_get_backup.return_value = "/path/to/backup"

        with patch("hub.services.update.restore_from_backup") as mock_restore:
            mock_restore.return_value = {"success": True}

            with patch("hub.services.update.get_db") as mock_get_db:
                mock_db = MagicMock()
                mock_get_db.return_value = mock_db
                mock_db.execute.return_value = mock_db
                mock_db.commit.return_value = None

                result = update.rollback_update()

                assert result["status"] == "success"
                assert "Rollback completed successfully" in result["message"]
                assert "timestamp" in result


def test_create_backup_before_update():
    """Test the create_backup_before_update function."""
    with patch("os.makedirs"):
        with patch("shutil.copy2"):
            with patch("builtins.open"):
                with patch("json.dump"):
                    with patch("os.getcwd", return_value="/test"):
                        with patch("hub.services.update._get_instance_path", return_value="/test/instance"):
                            result = update.create_backup_before_update()

                            assert "success" in result
                            assert result["success"] is True


def test_get_most_recent_backup():
    """Test the get_most_recent_backup function."""
    with patch("os.path.exists", return_value=True):
        with patch("os.listdir", return_value=["backup_pre_update_20230101_120000"]):
            with patch("os.path.isdir", return_value=True):
                with patch("os.path.getctime", return_value=1234567890):
                    with patch("hub.services.update._get_instance_path", return_value="/test/instance"):
                        result = update.get_most_recent_backup()

                        assert result is not None


def test_restore_from_backup():
    """Test the restore_from_backup function."""
    with patch("os.path.exists", return_value=True):
        with patch("shutil.copy2"):
            result = update.restore_from_backup("/test/backup")

            assert "success" in result
            assert result["success"] is True


def test_schedule_update_check():
    """Test the schedule_update_check function."""
    result = update.schedule_update_check()

    assert result["status"] == "not_implemented"
    assert "not yet implemented" in result["message"]


def test_get_update_schedule():
    """Test the get_update_schedule function."""
    result = update.get_update_schedule()

    assert "enabled" in result
    assert "frequency" in result
    assert "next_check" in result
    assert "last_check" in result


def test_graceful_update_shutdown():
    """Test the graceful_update_shutdown function."""
    with patch("hub.services.update.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.execute.return_value = mock_db
        mock_db.commit.return_value = None

        result = update.graceful_update_shutdown()

        assert result["status"] == "success"
        assert "Graceful shutdown completed" in result["message"]
