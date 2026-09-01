"""Tests for the admin API routes."""

import json
from unittest.mock import MagicMock, patch

import pytest

# HTTP Status Codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429


def test_admin_login(client):
    """Test admin login endpoint."""
    with patch("hub.services.authenticate_admin") as mock_auth:
        mock_auth.return_value = True

        response = client.post("/api/admin/login", json={"username": "admin", "password": "password"})
        assert response.status_code == HTTP_OK
        data = response.get_json()
        assert data["status"] == "success"


def test_admin_login_failure(client):
    """Test admin login endpoint with invalid credentials."""
    with patch("hub.services.authenticate_admin") as mock_auth:
        mock_auth.return_value = False

        response = client.post("/api/admin/login", json={"username": "admin", "password": "wrong"})
        assert response.status_code == HTTP_UNAUTHORIZED
        data = response.get_json()
        assert data["status"] == "error"


def test_admin_logout(client):
    """Test admin logout endpoint."""
    response = client.post("/api/admin/logout")
    assert response.status_code == HTTP_OK
    data = response.get_json()
    assert data["status"] == "success"


def test_get_admin_config_with_mocked_auth(client):
    """Test getting admin configuration with mocked IP whitelisting."""
    # Mock the IP whitelisting decorator
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        # Mock the decorator to just return the original function
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.get_config_for_admin") as mock_get_config:
            mock_get_config.return_value = {"test": "config"}

            response = client.get("/api/admin/config")
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert "test" in data


def test_update_admin_config_with_mocked_auth(client):
    """Test updating admin configuration with mocked IP whitelisting."""
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.update_config_from_admin") as mock_update_config:
            mock_update_config.return_value = True

            response = client.put("/api/admin/config", json={"layout": {"main_view": "week_calendar"}})
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert data["status"] == "success"


def test_get_system_info_with_mocked_auth(client):
    """Test getting system information with mocked IP whitelisting."""
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.get_system_info") as mock_get_sys_info:
            mock_get_sys_info.return_value = {
                "application": {"name": "Kitchen Hub", "version": "0.1.0"},
                "system": {"platform": "test", "cpu_percent": 10.0},
            }

            response = client.get("/api/admin/system")
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert "application" in data


def test_run_diagnostics_with_mocked_auth(client):
    """Test running diagnostics with mocked IP whitelisting."""
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.run_diagnostics") as mock_run_diag:
            mock_run_diag.return_value = {
                "timestamp": "2023-01-01T00:00:00",
                "checks": {"database": {"status": "ok", "message": "Connected"}},
            }

            response = client.get("/api/admin/diagnostics")
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert "checks" in data


def test_list_backups_with_mocked_auth(client):
    """Test listing backups with mocked IP whitelisting."""
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.list_backups") as mock_list_backups:
            mock_list_backups.return_value = [
                {
                    "name": "test_backup.tar.gz",
                    "size": 1024,
                    "modified": "2023-01-01T00:00:00",
                    "path": "/backups/test_backup.tar.gz",
                }
            ]

            response = client.get("/api/admin/backup")
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert len(data) == 1
            assert data[0]["name"] == "test_backup.tar.gz"


def test_create_backup_with_mocked_auth(client):
    """Test creating backup with mocked IP whitelisting."""
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.create_backup") as mock_create_backup:
            mock_create_backup.return_value = "/backups/test_backup.tar.gz"

            response = client.post("/api/admin/backup", json={"name": "test_backup.tar.gz"})
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert data["status"] == "success"


def test_get_backup_info_with_mocked_auth(client):
    """Test getting backup information with mocked IP whitelisting."""
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.get_backup_info") as mock_get_backup_info:
            mock_get_backup_info.return_value = {
                "name": "test_backup.tar.gz",
                "size": 1024,
                "modified": "2023-01-01T00:00:00",
                "path": "/backups/test_backup.tar.gz",
                "contents": [{"name": "test.db", "size": 512, "type": "file"}],
            }

            response = client.get("/api/admin/backup/test_backup.tar.gz")
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert data["name"] == "test_backup.tar.gz"


def test_delete_backup_with_mocked_auth(client):
    """Test deleting backup with mocked IP whitelisting."""
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.delete_backup") as mock_delete_backup:
            mock_delete_backup.return_value = True

            response = client.delete("/api/admin/backup/test_backup.tar.gz")
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert data["status"] == "success"


def test_restore_backup_with_mocked_auth(client):
    """Test restoring backup with mocked IP whitelisting."""
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.restore_backup") as mock_restore_backup:
            mock_restore_backup.return_value = True

            response = client.post("/api/admin/restore/test_backup.tar.gz")
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert data["status"] == "success"


def test_check_for_updates_with_mocked_auth(client):
    """Test checking for updates with mocked IP whitelisting."""
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.check_for_updates") as mock_check_updates:
            mock_check_updates.return_value = {
                "has_updates": False,
                "current_version": "0.1.0",
                "latest_version": "0.1.0",
                "timestamp": "2023-01-01T00:00:00",
            }

            response = client.get("/api/admin/updates/check")
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert "has_updates" in data


def test_perform_update_with_mocked_auth(client):
    """Test performing update with mocked IP whitelisting."""
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.perform_update") as mock_perform_update:
            mock_perform_update.return_value = {
                "status": "success",
                "message": "Update applied",
                "timestamp": "2023-01-01T00:00:00",
            }

            response = client.post("/api/admin/updates", json={"type": "latest"})
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert data["status"] == "success"


def test_get_update_history_with_mocked_auth(client):
    """Test getting update history with mocked IP whitelisting."""
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.get_update_history") as mock_get_history:
            mock_get_history.return_value = {"history": [], "last_check": "2023-01-01T00:00:00"}

            response = client.get("/api/admin/updates/history")
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert "history" in data


def test_rollback_update_with_mocked_auth(client):
    """Test rolling back update with mocked IP whitelisting."""
    with patch("hub.routes.api.require_ip_whitelist") as mock_require_ip:
        mock_require_ip.return_value = lambda f: f

        with patch("hub.services.rollback_update") as mock_rollback:
            mock_rollback.return_value = {
                "status": "success",
                "message": "Rollback completed",
                "timestamp": "2023-01-01T00:00:00",
            }

            response = client.post("/api/admin/updates/rollback")
            assert response.status_code == HTTP_OK
            data = response.get_json()
            assert data["status"] == "success"
