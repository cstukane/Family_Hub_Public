"""Helpers for persisting music provider state."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from flask import current_app

STATE_FILENAME = "music_provider_state.json"


def _state_path() -> str:
    instance_path = current_app.instance_path
    return os.path.join(instance_path, STATE_FILENAME)


def load_state() -> Dict[str, Any]:
    path = _state_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def save_state(state: Dict[str, Any]) -> None:
    path = _state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)


def get_active_provider_id() -> Optional[str]:
    state = load_state()
    return state.get("active_provider")


def set_active_provider_id(provider_id: str) -> None:
    state = load_state()
    state["active_provider"] = provider_id
    save_state(state)
