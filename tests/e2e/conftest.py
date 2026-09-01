"""E2E test fixtures: session-scoped Flask live server + Playwright page."""

import json
import os
import tempfile
import threading

import pytest
import yaml
from playwright.sync_api import Error as PlaywrightError
from werkzeug.serving import make_server

os.environ["LOG_FORMAT"] = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

from app import create_app
from hub.config import load_config
from hub.db import init_db


@pytest.fixture(scope="session")
def e2e_app():
    """Session-scoped Flask app for E2E tests (single server across all tests)."""
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)

    app = create_app()
    app.config["TESTING"] = True
    app.config["DATABASE"] = db_path
    app.config["SECRET_KEY"] = "e2e-test-secret-key"

    test_config_data = {
        "layout": {
            "main_view": "week_calendar",
            "sidebar": ["weather"],
        },
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
            "sports": {"kind": "espn", "favorite_teams": ["NYY"]},
        },
        "features": {"voice": False, "kiosk": False, "auth": False, "sports_ticker_enabled": True},
        "ui": {"theme": "light", "density": "comfortable"},
        "security": {
            "ssl_enabled": False,
            "ssl_cert_path": "",
            "ssl_key_path": "",
            "rate_limit_enabled": False,
            "default_rate_limit": "1000 per minute",
            "admin_rate_limit": "1000 per minute",
            "ip_whitelist_enabled": False,
            "ip_whitelist": [],
            "session_timeout": 3600,
            "secure_headers": False,
            "admin_username": None,
            "admin_password_hash": None,
            "admin_enabled": False,
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
        yaml.dump(test_config_data, f)
        config_path = f.name

    app.config["CONFIG"] = load_config(config_path)
    app.config["CONFIG_PATH"] = config_path

    with open(os.path.join("static", "mock", "sports_ticker.json"), "r", encoding="utf-8") as sports_file:
        sports_mock_payload = json.load(sports_file)

    from hub.services import sports_ticker_service

    sports_ticker_service.get_sports_ticker_data = lambda *args, **kwargs: sports_mock_payload

    with app.app_context():
        init_db()
        if hasattr(app, "scheduler") and app.scheduler.running:
            app.scheduler.shutdown()

    yield app

    os.unlink(db_path)
    os.unlink(config_path)


@pytest.fixture(scope="session")
def browser(launch_browser):
    """Skip dashboard e2e checks cleanly when Playwright browsers are not installed locally."""
    try:
        browser_instance = launch_browser()
    except PlaywrightError as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip("Playwright browser binaries are not installed in this environment.")
        raise

    yield browser_instance
    browser_instance.close()


@pytest.fixture(scope="session")
def live_server_url(e2e_app):
    """Start Flask on a random port and return the base URL."""
    server = make_server("127.0.0.1", 0, e2e_app)
    port = server.socket.getsockname()[1]
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
