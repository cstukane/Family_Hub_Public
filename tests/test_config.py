import os
import tempfile
from pathlib import Path

import pytest
import yaml

from hub.config import AppConfig, ConfigSchema, FeaturesConfig, UIConfig, WeatherLocation, WeatherProvider, load_config

# Test constants
LATITUDE = 40.90
LONGITUDE = -74.55


def test_config_schema_validation():
    """Test that the config schema properly validates."""
    config_data = {
        "layout": {"main_view": "week_calendar", "sidebar": ["notes", "shopping", "weather"]},
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
            "weather": {"kind": "open_meteo", "location": {"lat": LATITUDE, "lon": LONGITUDE}},
        },
        "features": {"voice": False, "kiosk": True, "auth": False},
        "ui": {"theme": "auto", "density": "comfortable"},
    }

    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
        yaml.dump(config_data, f)
        config_path = f.name

    # Test loading the config
    config = load_config(config_path)

    # Verify that it has the expected structure
    assert config.layout["main_view"] == "week_calendar"
    assert "notes" in config.layout["sidebar"]
    assert len(config.apps) == 1
    assert config.apps[0].id == "calendar"
    # Access providers as a dict rather than an object attribute
    assert config.providers["weather"]["kind"] == "open_meteo"

    # Clean up

    os.unlink(config_path)


def test_config_with_invalid_data():
    """Test config loading with invalid data raises error."""
    # Create invalid config data
    invalid_config_data = {
        "layout": "invalid",  # Should be a dict
        "apps": "invalid",  # Should be a list
        "providers": {},
        "features": {},
        "ui": {},
    }

    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
        yaml.dump(invalid_config_data, f)
        config_path = f.name

    # Test that loading raises an error
    with pytest.raises(ValueError):
        load_config(config_path)

    # Clean up

    os.unlink(config_path)


def test_config_schema_model():
    """Test creating ConfigSchema model directly."""
    features = FeaturesConfig(voice=False, kiosk=True, auth=False)
    assert not features.voice
    assert features.kiosk

    ui = UIConfig(theme="auto", density="comfortable")
    assert ui.theme == "auto"

    location = WeatherLocation(lat=LATITUDE, lon=LONGITUDE)
    assert location.lat == LATITUDE

    app = AppConfig(id="test", label="Test App", icon="test.svg", action="switch_view", target="test_view")
    assert app.id == "test"
    assert app.label == "Test App"


def test_example_config_is_safe_and_local_env_overrides(tmp_path, monkeypatch):
    example = load_config("config.example.yaml")
    assert example.commute.home_address == ""
    assert example.commute.work_address == ""
    assert example.commute.mapbox_token == ""
    assert not example.iot.enabled
    assert not example.features.plugins

    config_path = tmp_path / "config.yaml"
    config_path.write_text(Path("config.example.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / ".env").write_text("COMMUTE_MAPBOX_TOKEN=local-token\n", encoding="utf-8")
    monkeypatch.delenv("COMMUTE_MAPBOX_TOKEN", raising=False)
    loaded = load_config(str(config_path))
    assert loaded.commute.mapbox_token == "local-token"


def test_public_config_excludes_server_side_commute_fields(app):
    from hub.routes.main import build_public_config

    config = load_config("config.example.yaml")
    config.commute.home_address = "private home"
    config.commute.work_address = "private work"
    config.commute.mapbox_token = "private token"
    config.commute.google_api_key = "private key"

    with app.test_request_context():
        public = build_public_config(config)
    assert set(public["commute"]) == {
        "enabled",
        "always_visible",
        "morning_window",
        "evening_window",
        "refresh_minutes",
    }
    serialized = str(public)
    assert "private home" not in serialized
    assert "private work" not in serialized
    assert "private token" not in serialized
    assert "private key" not in serialized
