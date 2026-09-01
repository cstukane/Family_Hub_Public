import shutil
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import yaml

from app import create_app

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / "instance" / "test_tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_test_dir():
    path = TEST_TMP_ROOT / f"service_gating_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_test_config(tmp_path):
    """Create a minimal config file with optional services disabled."""
    config_data = {
        "layout": {"main_view": "week_calendar", "sidebar": ["notes", "shopping"]},
        "apps": [
            {
                "id": "calendar",
                "label": "Calendar",
                "icon": "calendar.svg",
                "action": "switch_view",
                "target": "week_calendar",
            }
        ],
        "providers": {
            "calendar": {"kind": "ics", "ics_url": "https://example.com/family.ics"},
            "weather": {"kind": "open_meteo", "location": {"lat": 40.0, "lon": -74.0}},
            "sports": {"kind": "espn"},
        },
        "features": {
            "voice": False,
            "kiosk": True,
            "auth": False,
            "sports_ticker_enabled": True,
        },
        "services": {
            "weather_alerts": False,
        },
        "ui": {"theme": "auto", "density": "comfortable"},
        "security": {
            "ssl_enabled": False,
            "ssl_cert_path": "",
            "ssl_key_path": "",
            "rate_limit_enabled": False,
            "default_rate_limit": "100 per minute",
            "admin_rate_limit": "100 per minute",
            "ip_whitelist_enabled": False,
            "ip_whitelist": [],
            "session_timeout": 3600,
            "secure_headers": False,
            "admin_username": None,
            "admin_password_hash": None,
            "admin_enabled": False,
        },
        "casting": {"enabled": False, "discovery_enabled": False, "devices": []},
        "photos": {"enabled": False, "local_path": "./instance/photos", "sync_enabled": False},
        "music": {"enabled": False, "local_path": "./instance/music", "sync_enabled": False},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")
    return str(config_path)


def test_optional_services_disabled_do_not_start_threads():
    """Ensure edge service and casting discovery do not start when disabled."""
    tmp_path = _make_test_dir()
    config_path = _write_test_config(tmp_path)
    app = None

    try:
        with (
            patch("hub.db.init_app"),
            patch("hub.db.init_db"),
            patch("hub.db.init_admin_account"),
            patch("hub.services.casting_manager.refresh_device_list") as mock_casting_refresh,
        ):
            app = create_app(config_path)

        job_ids = [job.id for job in app.scheduler.get_jobs()]
        # Core jobs should remain scheduled
        assert "weather_refresh" in job_ids
        assert "calendar_refresh" in job_ids
        assert "sports_ticker_refresh" in job_ids
        # Optional jobs should be skipped
        assert "casting_device_discovery" not in job_ids
        assert "weather_alert_monitor" not in job_ids
        assert "update_check" not in job_ids
        assert "webhook_status_check" not in job_ids
        mock_casting_refresh.assert_not_called()
    finally:
        if app is not None and hasattr(app, "scheduler") and app.scheduler.running:
            app.scheduler.shutdown()
        shutil.rmtree(tmp_path, ignore_errors=True)
