"""Runtime-root behavior tests."""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

for mod_name in list(sys.modules):
    if mod_name == "hub" or mod_name.startswith("hub."):
        del sys.modules[mod_name]

from hub.utils.runtime import get_runtime_root  # noqa: E402


def test_runtime_root_defaults_to_repo_local_instance(tmp_path, monkeypatch):
    monkeypatch.delenv("FAMILY_HUB_INSTANCE_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "instance").mkdir()

    assert get_runtime_root() == str(tmp_path / "instance")


def test_runtime_root_honors_instance_path(monkeypatch, tmp_path):
    instance_root = tmp_path / "custom_instance"
    instance_root.mkdir()
    monkeypatch.setenv("FAMILY_HUB_INSTANCE_PATH", str(instance_root))

    assert get_runtime_root() == str(instance_root)


def test_runtime_root_config_env_does_not_override_instance_path(monkeypatch, tmp_path):
    config_dir = tmp_path / "config_dir"
    config_dir.mkdir()
    instance_root = tmp_path / "custom_instance"
    instance_root.mkdir()
    monkeypatch.setenv("FAMILY_HUB_CONFIG", str(config_dir / "config.yaml"))
    monkeypatch.setenv("FAMILY_HUB_INSTANCE_PATH", str(instance_root))

    assert get_runtime_root() == str(instance_root)


def test_runtime_root_uses_app_instance_path(monkeypatch, tmp_path):
    monkeypatch.delenv("FAMILY_HUB_INSTANCE_PATH", raising=False)

    from flask import Flask

    app = Flask(__name__)
    app.instance_path = str(tmp_path / "app_instance")

    with app.app_context():
        assert get_runtime_root() == str(tmp_path / "app_instance")


def test_default_config_path_prefers_config_env(monkeypatch, tmp_path):
    config_path = tmp_path / "deploy" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text("layout: {}\n", encoding="utf-8")
    monkeypatch.setenv("FAMILY_HUB_CONFIG", str(config_path))

    app_py = PROJECT_ROOT / "app.py"
    app_spec = importlib.util.spec_from_file_location("runtime_app", app_py)
    app_module = importlib.util.module_from_spec(app_spec)
    app_spec.loader.exec_module(app_module)

    assert app_module._default_config_path() == str(config_path)


def test_default_config_path_falls_back_to_instance_config(monkeypatch, tmp_path):
    monkeypatch.delenv("FAMILY_HUB_CONFIG", raising=False)
    instance_root = tmp_path / "custom_instance"
    instance_root.mkdir()
    config_path = instance_root / "config.yaml"
    config_path.write_text("layout: {}\n", encoding="utf-8")
    monkeypatch.setenv("FAMILY_HUB_INSTANCE_PATH", str(instance_root))

    app_py = PROJECT_ROOT / "app.py"
    app_spec = importlib.util.spec_from_file_location("runtime_app", app_py)
    app_module = importlib.util.module_from_spec(app_spec)
    app_spec.loader.exec_module(app_module)

    assert app_module._default_config_path() == str(config_path)


def test_default_config_path_falls_back_to_example_when_no_instance_config(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("FAMILY_HUB_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "instance").mkdir()

    app_py = PROJECT_ROOT / "app.py"
    app_spec = importlib.util.spec_from_file_location("runtime_app", app_py)
    app_module = importlib.util.module_from_spec(app_spec)
    app_spec.loader.exec_module(app_module)

    assert app_module._default_config_path() == "config.example.yaml"
