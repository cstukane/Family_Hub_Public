import os
import tempfile
from importlib.util import find_spec
from pathlib import Path

import pytest
import yaml

from app import create_app
from hub.config import load_config
from hub.db import init_db

WORKSPACE_TEMP_DIR = Path(__file__).resolve().parents[1] / "instance" / "test_tmp"
WORKSPACE_TEMP_DIR.mkdir(parents=True, exist_ok=True)
os.environ["TMP"] = str(WORKSPACE_TEMP_DIR)
os.environ["TEMP"] = str(WORKSPACE_TEMP_DIR)
os.environ["TMPDIR"] = str(WORKSPACE_TEMP_DIR)
os.environ["LOG_FORMAT"] = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
tempfile.tempdir = str(WORKSPACE_TEMP_DIR)


collect_ignore_glob = []


def _module_available(module_name: str) -> bool:
    try:
        return find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


if not _module_available("playwright.sync_api") or not _module_available("pytest_playwright.pytest_playwright"):
    collect_ignore_glob.append("e2e/*.py")


@pytest.fixture
def app():
    """Create application for testing."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)

    # Create app with test configuration
    app = create_app()
    app.config["TESTING"] = True
    app.config["DATABASE"] = db_path
    app.config["SECRET_KEY"] = "test-secret-key"  # Add a secret key

    # Load a simple test config

    # Create a simple test config with explicit security settings
    test_config_data = {
        "layout": {"main_view": "week_calendar", "sidebar": ["notes", "shopping", "weather"]},
        "apps": [
            {
                "id": "calendar",
                "label": "Calendar",
                "icon": "calendar.svg",
                "action": "switch_view",
                "target": "week_calendar",
            },
            {
                "id": "youtube",
                "label": "YouTube",
                "icon": "youtube.svg",
                "action": "open_iframe",
                "url": "https://www.youtube.com/",
            },
        ],
        "providers": {
            "calendar": {"kind": "ics", "ics_url": "https://example.com/family.ics"},
            "weather": {"kind": "open_meteo", "location": {"lat": 40.90, "lon": -74.55}},
        },
        "features": {"voice": False, "kiosk": True, "auth": False},
        "ui": {"theme": "auto", "density": "comfortable"},
        "security": {
            "ssl_enabled": False,
            "ssl_cert_path": "",
            "ssl_key_path": "",
            "rate_limit_enabled": False,  # Disable rate limiting in tests
            "default_rate_limit": "1000 per minute",
            "admin_rate_limit": "1000 per minute",
            "ip_whitelist_enabled": False,
            "ip_whitelist": [],
            "session_timeout": 3600,
            "secure_headers": False,  # Disable HTTPS enforcement in tests
            "admin_username": None,
            "admin_password_hash": None,
            "admin_enabled": False,
        },
    }

    # Write test config to a temporary file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
        yaml.dump(test_config_data, f)
        config_path = f.name

    # Load the test config
    app.config["CONFIG"] = load_config(config_path)
    app.config["CONFIG_PATH"] = config_path

    # Create the database tables
    with app.app_context():
        init_db()

        # Stop the scheduler to avoid background jobs during tests
        if hasattr(app, "scheduler") and app.scheduler.running:
            app.scheduler.shutdown()

    yield app

    # Clean up
    os.unlink(db_path)
    os.unlink(config_path)


@pytest.fixture
def client(app):
    """Create test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner for the app."""
    return app.test_cli_runner()
