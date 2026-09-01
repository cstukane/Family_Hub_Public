"""Sports service for the Kitchen Hub application."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from flask import current_app

from hub.adapters.sports_espn import ESPNAdapter
from hub.adapters.sports_thesportsdb import TheSportsDBAdapter
from hub.cache import get_cache, set_cache
from hub.models import SportsData


def _get_adapter():
    """Get the appropriate sports adapter based on configuration."""
    config = current_app.config.get("CONFIG")
    if not config or not hasattr(config, "providers"):
        # Fallback to TheSportsDB
        return TheSportsDBAdapter()

    sports_config = config.providers.get("sports", {})
    provider_kind = sports_config.get("kind", "thesportsdb")

    if provider_kind == "espn":
        return ESPNAdapter()
    else:
        # Default to TheSportsDB
        api_key = sports_config.get("api_key")
        return TheSportsDBAdapter(api_key=api_key)


def get_sports_data(favorite_teams: Optional[List[str]] = None) -> SportsData:
    """Get sports data with caching."""
    if favorite_teams is None:
        config = current_app.config.get("CONFIG")
        if config and hasattr(config, "providers"):
            sports_config = config.providers.get("sports", {})
            favorite_teams = sports_config.get("favorite_teams", [])
        else:
            favorite_teams = []

    # Create cache key based on whether we're using favorite teams
    use_favorite_teams = bool(favorite_teams and len(favorite_teams) > 0)
    cache_key = f"sports_data_{'with_favorites' if use_favorite_teams else 'main_only'}_{'_'.join(sorted(favorite_teams)) if use_favorite_teams else 'main'}"

    # Try to get from cache first
    cached_data = get_cache(cache_key)
    if cached_data:
        last_updated_raw = cached_data.get("last_updated")
        parsed_last_updated = None
        if isinstance(last_updated_raw, str):
            try:
                parsed_last_updated = datetime.fromisoformat(last_updated_raw)
            except ValueError:
                parsed_last_updated = None
        elif isinstance(last_updated_raw, datetime):
            parsed_last_updated = last_updated_raw

        # Return cached data with the original format; allow dict-backed games for template compatibility
        return SportsData(
            games=cached_data.get("games", []),
            last_updated=parsed_last_updated,
            source=cached_data.get("source", "cached"),
        )

    # If not in cache, fetch from adapter
    adapter = _get_adapter()
    try:
        # Get main sports stories (all games)
        main_sports_data = adapter.get_sports_data(None)  # No filtering for main stories

        if use_favorite_teams:
            # Also get favorite team games
            favorite_sports_data = adapter.get_sports_data(favorite_teams)

            # Combine both sets of games, avoiding duplicates
            all_games = main_sports_data.games.copy()

            # Add favorite team games that aren't already in the main list (avoiding duplicates)
            favorite_team_ids = {game.id for game in all_games if game.id}  # Get IDs of main games
            for game in favorite_sports_data.games:
                if game.id not in favorite_team_ids:
                    all_games.append(game)

            # Create combined sports data with all games
            combined_sports_data = SportsData(
                games=all_games,
                last_updated=max(
                    main_sports_data.last_updated,
                    favorite_sports_data.last_updated,
                    # In case one of them is None
                    main_sports_data.last_updated or favorite_sports_data.last_updated or None,
                ),
                source=f"{main_sports_data.source}_with_favorites",
            )
            sports_data = combined_sports_data
        else:
            # Just return main sports stories
            sports_data = main_sports_data

        # Cache the data (cache for 10 minutes)
        set_cache(cache_key, sports_data.to_dict(), ttl_seconds=600)

        return sports_data
    except Exception as e:
        logging.error(f"Error fetching sports data: {e}")
        # Return main sports data if there's an error combining with favorites
        return get_main_sports_data(adapter)


def get_main_sports_data(adapter) -> SportsData:
    """Get main sports stories only."""
    try:
        return adapter.get_sports_data(None)  # No team filtering for main stories
    except Exception as e:
        logging.error(f"Error fetching main sports data: {e}")
        return SportsData(games=[], source="error")


def refresh_sports_data() -> bool:
    """Force refresh sports data by clearing cache and fetching fresh data."""
    try:
        config = current_app.config.get("CONFIG")
        if config and hasattr(config, "providers"):
            sports_config = config.providers.get("sports", {})
            favorite_teams = sports_config.get("favorite_teams", [])
        else:
            favorite_teams = []

        cache_key = f"sports_data_{'_'.join(sorted(favorite_teams)) if favorite_teams else 'all'}"

        # Clear the cache for this key
        from hub.cache import delete_cache

        delete_cache(cache_key)

        # Fetch fresh data
        adapter = _get_adapter()
        sports_data = adapter.get_sports_data(favorite_teams)

        # Set the fresh data in cache
        set_cache(cache_key, sports_data.to_dict(), ttl_seconds=600)

        return True
    except Exception as e:
        logging.error(f"Error refreshing sports data: {e}")
        return False


def get_team_info(team_name: str) -> Optional[Dict]:
    """Get information about a specific team."""
    try:
        adapter = _get_adapter()
        team = adapter.get_team_info(team_name)
        if team:
            return team.to_dict()
        return None
    except Exception as e:
        logging.error(f"Error fetching team info: {e}")
        return None


def get_available_leagues() -> Optional[List[Dict]]:
    """Get available leagues."""
    try:
        adapter = _get_adapter()
        return adapter.get_leagues()
    except Exception as e:
        logging.error(f"Error fetching available leagues: {e}")
        return []


def update_favorite_teams(new_favorite_teams: List[str]) -> bool:
    """Update favorite teams in persistent config and in-memory app config."""
    normalized = []
    seen = set()
    for team in new_favorite_teams:
        if not isinstance(team, str):
            continue
        trimmed = team.strip().lower()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        normalized.append(trimmed)

    try:
        import yaml
        from flask import current_app

        config_path = current_app.config.get("CONFIG_PATH", "config.yaml")

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

        config_data.setdefault("providers", {})
        config_data["providers"].setdefault("sports", {})
        config_data["providers"]["sports"]["favorite_teams"] = normalized

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)

        app_config = current_app.config.get("CONFIG")
        if app_config is not None:
            from hub.utils.config_helpers import update_config_favorite_teams_in_memory

            update_config_favorite_teams_in_memory(app_config, normalized)
            current_app.config["CONFIG"] = app_config

        logging.info(f"Favorite teams updated to: {normalized}")
        return True
    except Exception as e:
        logging.error(f"Error updating favorite teams in config: {e}")
        return False
