"""Utility functions for working with configuration, particularly for extracting favorite teams."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Sequence, Union

if TYPE_CHECKING:
    from hub.config import AppConfig


def get_config_dict(config: Union["AppConfig", Dict]) -> Dict:
    """
    Convert a config object (Pydantic model or dict) to a standard dict.

    Args:
        config: The configuration object (either Pydantic model or dict)

    Returns:
        A dictionary representation of the config
    """
    if hasattr(config, "model_dump"):
        return config.model_dump()
    elif hasattr(config, "dict"):
        return config.dict()
    elif isinstance(config, dict):
        return config
    else:
        # If it's neither a model with .dict()/.model_dump() nor a dict, return as-is
        # This shouldn't happen in normal operation, but return empty dict as fallback
        return {}


def get_config_value(config: Union["AppConfig", Dict, None], path: Sequence[str], default=None):
    """
    Fetch a nested config value regardless of whether the config is a model or dict.

    Args:
        config: The configuration object (Pydantic model, dict, or None)
        path: Sequence of keys/attributes to traverse
        default: Fallback if any portion of the path is missing

    Returns:
        The resolved value or default when not found
    """
    current = config
    for key in path:
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(key)
        elif hasattr(current, key):
            current = getattr(current, key)
        elif hasattr(current, "get"):
            try:
                current = current.get(key)
            except TypeError:
                return default
        else:
            return default
    return current if current is not None else default


def get_favorite_teams_from_config(config: Union["AppConfig", Dict]) -> List[str]:
    """
    Extract favorite teams from config regardless of whether it's a Pydantic model or dict.

    Args:
        config: The configuration object (either Pydantic model or dict)

    Returns:
        A list of favorite teams
    """
    # Convert config to a dictionary first
    config_dict = get_config_dict(config)

    # Extract favorite teams using dictionary access
    favorite_teams = config_dict.get("providers", {}).get("sports", {}).get("favorite_teams", [])

    # Ensure we return a list, even if None was found
    return favorite_teams if isinstance(favorite_teams, list) else []


def update_config_favorite_teams_in_memory(app_config: Union["AppConfig", Dict], normalized_teams: List[str]) -> bool:
    """
    Update favorite teams in memory config, handling both Pydantic model and dict configs.

    Args:
        app_config: The in-memory app configuration object
        normalized_teams: The list of normalized favorite teams to update

    Returns:
        True if successful, False otherwise
    """
    # Handle Pydantic model config
    if hasattr(app_config, "providers"):
        providers = getattr(app_config, "providers", None)
        if providers is not None and hasattr(providers, "sports"):
            sports_cfg = getattr(providers, "sports", None)
            if sports_cfg is not None:
                try:
                    setattr(sports_cfg, "favorite_teams", list(normalized_teams))
                    return True
                except AttributeError:
                    pass
        # Handle dict-based providers
        elif isinstance(providers, dict):
            sports_cfg = providers.setdefault("sports", {})
            if isinstance(sports_cfg, dict):
                sports_cfg["favorite_teams"] = list(normalized_teams)
                return True

    # Handle pure dict config
    elif isinstance(app_config, dict):
        providers = app_config.setdefault("providers", {})
        sports_cfg = providers.setdefault("sports", {})
        sports_cfg["favorite_teams"] = list(normalized_teams)
        return True

    return False
