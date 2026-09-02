"""Sports ticker service for the Family Hub application."""

import json
import logging
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set

import requests
from flask import current_app, has_app_context

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

from hub.data.team_catalog import TEAM_CATALOG, build_alias_lookup
from hub.models import SportsData
from hub.utils.http import RateLimitError, rate_limited_get

LIVE_CACHE_MAX_AGE_SECONDS = 90
IDLE_CACHE_MAX_AGE_SECONDS = 300
EMPTY_CACHE_MAX_AGE_SECONDS = 120
FUTURE_LOOKAHEAD_DAYS = 3
DEFAULT_DISPLAY_TIMEZONE_NAME = "UTC"

if ZoneInfo:
    try:
        DISPLAY_TIMEZONE = ZoneInfo(DEFAULT_DISPLAY_TIMEZONE_NAME)
    except Exception:
        DISPLAY_TIMEZONE = timezone.utc
else:
    DISPLAY_TIMEZONE = timezone.utc

# Metrics tracking for sports ticker
FETCH_LATENCY_METRICS = []
CACHE_WRITE_DURATION_METRICS = []
FETCH_COUNT = 0
CACHE_HIT_COUNT = 0
CACHE_MISS_COUNT = 0

# Dedup guard: only one background refresh at a time
_REFRESH_LOCK = threading.Lock()


def _get_cache_file_path() -> str:
    """Get the path to the sports ticker cache file."""
    # Use Flask's instance path, ensuring we are strictly inside a request context or app context
    cache_dir = os.path.join(current_app.instance_path, "cache")

    os.makedirs(cache_dir, exist_ok=True)

    # Create the cache file path
    return os.path.join(cache_dir, "sports_ticker.json")


def _get_backup_file_paths() -> List[str]:
    """Get paths for backup cache files (latest + two backups)."""
    cache_dir = os.path.join(current_app.instance_path, "cache")

    os.makedirs(cache_dir, exist_ok=True)

    # Return paths for backup files
    return [
        os.path.join(cache_dir, "sports_ticker.json.backup1"),
        os.path.join(cache_dir, "sports_ticker.json.backup2"),
        os.path.join(cache_dir, "sports_ticker.json.backup3"),
    ]


def _atomic_write_cache_file(path: str, data: Dict) -> bool:
    """Write data to cache file using atomic write to avoid corruption."""
    global CACHE_WRITE_DURATION_METRICS

    start_time = time.time()
    try:
        # Create a temporary file in the same directory
        temp_path = f"{path}.tmp"

        # Write data to temporary file
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Atomically replace the original file with the temp file
        os.replace(temp_path, path)

        # Record cache write duration metric
        duration = time.time() - start_time
        CACHE_WRITE_DURATION_METRICS.append(duration)

        # Keep only the latest 100 metrics to prevent memory bloat
        if len(CACHE_WRITE_DURATION_METRICS) > 100:
            CACHE_WRITE_DURATION_METRICS = CACHE_WRITE_DURATION_METRICS[-100:]

        return True
    except Exception as e:
        logging.error(f"Error writing cache file atomically: {e}")
        # Clean up temp file if it exists
        temp_path = f"{path}.tmp"
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:  # nosec B110
                pass
        return False


def _rotate_cache_files() -> bool:
    """Rotate cache files, keeping latest + two backups."""
    try:
        main_path = _get_cache_file_path()
        backup_paths = _get_backup_file_paths()

        # Rotate: backup3 <- backup2 <- backup1 <- current main file
        for i in range(len(backup_paths) - 1, -1, -1):
            source = backup_paths[i - 1] if i > 0 else main_path
            dest = backup_paths[i]

            if os.path.exists(source):
                # Only copy if source is different from destination
                if source != dest:
                    # Copy source to destination
                    import shutil

                    shutil.copy2(source, dest)

        return True
    except Exception as e:
        logging.error(f"Error rotating cache files: {e}")
        return False


def _read_cache_file() -> Optional[Dict]:
    """Read data from the cache file."""
    global CACHE_HIT_COUNT, CACHE_MISS_COUNT

    cache_path = _get_cache_file_path()

    if not os.path.exists(cache_path):
        CACHE_MISS_COUNT += 1
        return None

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Add cache metadata
        if "meta" not in data:
            data["meta"] = {}

        # Calculate cache age
        updated_at_str = data.get("updated_at")
        cache_age_seconds: Optional[int] = None
        if updated_at_str:
            try:
                updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                cache_age_seconds = int((datetime.now(timezone.utc) - updated_at).total_seconds())
            except Exception:
                cache_age_seconds = None
        data["meta"]["cache_age_seconds"] = cache_age_seconds if cache_age_seconds is not None else 0
        data["meta"]["stale"] = _determine_cache_staleness(cache_age_seconds, data.get("games", []))

        CACHE_HIT_COUNT += 1

        return data
    except Exception as e:
        CACHE_MISS_COUNT += 1
        logging.error(f"Error reading cache file: {e}")
        return None


def _determine_cache_staleness(cache_age_seconds: Optional[int], games: List[Dict]) -> bool:
    """Determine whether cached data should be considered stale."""
    if cache_age_seconds is None:
        return True

    if not games:
        return cache_age_seconds > EMPTY_CACHE_MAX_AGE_SECONDS

    has_live_game = any((game.get("status") or "").lower() == "in_progress" for game in games)
    threshold = LIVE_CACHE_MAX_AGE_SECONDS if has_live_game else IDLE_CACHE_MAX_AGE_SECONDS
    return cache_age_seconds > threshold


def _filter_games_for_favorites(games: List[Dict], favorite_teams: Optional[List[str]]) -> List[Dict]:
    """
    Filter games to show:
    1. All games on the current day (upcoming, live, or final) regardless of favorite status
    2. Future games only for favorite teams
    This keeps the ticker relevant by showing today's games and future favorite team games.
    """
    if not games:
        return games

    favorites_lower: Set[str] = {
        fav.strip().lower() for fav in (favorite_teams or []) if isinstance(fav, str) and fav.strip()
    }

    for game in games:
        game["is_favorite"] = False
        game["is_future_favorite"] = False
        game["favorite_start_date"] = None
        game["favorite_start_time"] = None
        game["show_start_date"] = False

    if not favorites_lower:
        # If no favorites specified, return all games
        return games

    league_alias_cache: Dict[str, Dict[str, str]] = {}
    league_favorites: Dict[str, Set[str]] = {}
    recognized_aliases: Set[str] = set()

    for league_id in TEAM_CATALOG.keys():
        league_key = league_id.lower()
        alias_lookup = build_alias_lookup(league_key)
        league_alias_cache[league_key] = alias_lookup

        recognized_aliases.update(alias_lookup.keys())
        normalized_matches: Set[str] = {alias_lookup[fav] for fav in favorites_lower if fav in alias_lookup}
        if normalized_matches:
            league_favorites[league_key] = normalized_matches

    unmatched_favorites: Set[str] = favorites_lower - recognized_aliases

    now_utc = datetime.now(timezone.utc)
    try:
        today_local = datetime.now(DISPLAY_TIMEZONE).date()
    except Exception:
        today_local = datetime.now(timezone.utc).date()

    filtered_games: List[Dict] = []

    for game in games:
        league = (game.get("league") or "").lower()
        alias_lookup = league_alias_cache.get(league, {})
        normalized_favorites = league_favorites.get(league, set())

        matched_primary: Set[str] = _event_primary_matches(game, alias_lookup) if alias_lookup else set()
        is_favorite = bool(matched_primary and (matched_primary & normalized_favorites))

        if not is_favorite and unmatched_favorites:
            candidate_tokens: Set[str] = set()
            for side in ("home_team", "away_team"):
                team = game.get(side) or {}
                for key in ("name", "abbreviation"):
                    value = (team.get(key) or "").strip().lower()
                    if not value:
                        continue
                    candidate_tokens.add(value)
                    condensed = value.replace(".", "")
                    if condensed:
                        candidate_tokens.add(condensed)
                        candidate_tokens.update(part for part in condensed.split() if part)
                team_id = str(team.get("id") or "").strip().lower()
                if team_id:
                    candidate_tokens.add(team_id)
            if candidate_tokens & unmatched_favorites:
                is_favorite = True

        game["is_favorite"] = is_favorite

        start_dt = _parse_iso_datetime(game.get("start_time_utc") or game.get("start_time"))

        # Determine if game is today
        is_today = False
        if start_dt:
            try:
                game_date_local = start_dt.astimezone(DISPLAY_TIMEZONE).date()
            except Exception:
                game_date_local = start_dt.astimezone(timezone.utc).date()
            is_today = game_date_local == today_local

        # Only add game if it's scheduled for today OR if it's a favorite team game scheduled in the future
        should_include = False
        if is_today:
            # Include all games happening today (upcoming, live, or final)
            should_include = True
        elif is_favorite and start_dt and start_dt > now_utc and game.get("status") == "scheduled":
            # Include future games for favorite teams
            game["is_future_favorite"] = True
            try:
                local_dt = start_dt.astimezone(DISPLAY_TIMEZONE)
            except Exception:
                local_dt = start_dt.astimezone(timezone.utc)

            game["favorite_start_date"] = local_dt.strftime("%m/%d")
            game["favorite_start_time"] = local_dt.strftime("%I:%M %p").lstrip("0")
            game["show_start_date"] = local_dt.date() != today_local
            should_include = True
        elif is_favorite and (not start_dt or start_dt <= now_utc):
            # If it's a favorite team but no future game, still include if it's ongoing/final
            should_include = True

        if should_include:
            filtered_games.append(game)

    return filtered_games


def _normalize_favorites_for_league(favorite_teams: Optional[List[str]], league: str) -> (set, Dict[str, str]):
    """Normalize favorite teams for a specific league using the catalog alias lookup."""
    alias_lookup = build_alias_lookup(league)
    favorites_lower = {fav.lower() for fav in (favorite_teams or []) if isinstance(fav, str)}
    normalized: set = set()

    for favorite in favorites_lower:
        if favorite in alias_lookup:
            normalized.add(alias_lookup[favorite])
            continue

        matched_primary = None
        for alias, primary in alias_lookup.items():
            if favorite in alias or alias in favorite:
                matched_primary = primary
                break

        if matched_primary:
            normalized.add(matched_primary)

    return normalized, alias_lookup


def _event_primary_matches(event: Dict, alias_lookup: Dict[str, str]) -> set:
    """Return the set of primary teams (by catalog value) involved in an event."""
    matches: set = set()

    for side in ("home_team", "away_team"):
        team = event.get(side) or {}
        candidates = set()

        name = (team.get("name") or "").lower()
        abbreviation = (team.get("abbreviation") or "").lower()
        team_id = str(team.get("id") or "").lower()

        for value in (name, abbreviation):
            if value:
                candidates.add(value)
                candidates.add(value.replace(".", ""))
                candidates.update(value.replace(".", "").split())

        if team_id:
            candidates.add(team_id)

        for candidate in list(candidates):
            if not candidate:
                continue
            if candidate in alias_lookup:
                matches.add(alias_lookup[candidate])
            else:
                for alias, primary in alias_lookup.items():
                    if candidate in alias or alias in candidate:
                        matches.add(primary)
                        break

    return matches


def _prepare_cached_payload(data: Dict, favorite_teams: Optional[List[str]]) -> Dict:
    """Apply favorite prioritization and update cache metadata for a payload."""
    favorite_list = list(favorite_teams or [])
    data["games"] = _filter_games_for_favorites(data.get("games", []), favorite_list)

    meta = data.setdefault("meta", {})
    meta["favorites"] = favorite_list

    cache_age_seconds: Optional[int] = meta.get("cache_age_seconds")
    if cache_age_seconds is None:
        updated_at_str = data.get("updated_at")
        if updated_at_str:
            try:
                updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                cache_age_seconds = int((datetime.now(timezone.utc) - updated_at).total_seconds())
            except Exception:
                cache_age_seconds = None
        if cache_age_seconds is None:
            cache_age_seconds = 0

    meta["cache_age_seconds"] = cache_age_seconds
    meta["stale"] = _determine_cache_staleness(cache_age_seconds, data["games"])
    return data


def _build_placeholder_payload(favorite_teams: List[str]) -> Dict:
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "timezone": DEFAULT_DISPLAY_TIMEZONE_NAME,
            "cache_age_seconds": None,
            "stale": True,
            "favorites": favorite_teams,
            "source": "cache-miss",
            "fetch_error_reason": None,
            "consecutive_empty_count": 0,
            "should_hide": False,
        },
        "games": [],
    }


def _trigger_background_refresh(app, favorite_teams: List[str]) -> None:
    """Kick off a one-shot background refresh so the request thread can return stale cache quickly."""
    if not _REFRESH_LOCK.acquire(blocking=False):
        return  # refresh already in progress

    def _worker():
        try:
            with app.app_context():
                # Avoid spawning another background refresh from inside this call
                get_sports_ticker_data(favorite_teams, force_refresh=True, allow_background_refresh=False)
        except Exception as exc:
            logging.warning(f"Background ticker refresh failed: {exc}")
        finally:
            _REFRESH_LOCK.release()

    threading.Thread(target=_worker, daemon=True).start()


def request_background_refresh(favorite_teams: Optional[List[str]] = None) -> bool:
    """Schedule a background refresh without blocking the request thread."""
    try:
        from flask import current_app

        app = current_app._get_current_object()
    except Exception:
        return False

    favorite_teams = list(favorite_teams or [])
    _trigger_background_refresh(app, favorite_teams)
    return True


def _normalize_display_clock(clock_value: Optional[str]) -> Optional[str]:
    """Normalize ESPN display clock values, removing placeholders like 0:00."""
    if clock_value is None:
        return None

    clock = str(clock_value).strip()
    if not clock:
        return None

    upper_clock = clock.upper()
    placeholder_words = {"PREGAME", "PRE-GAME", "FINAL", "FINAL/OT", "POSTPONED", "PPD", "TBD", "DELAYED"}
    if upper_clock in placeholder_words:
        return None

    has_digit = any(ch.isdigit() for ch in clock)
    if has_digit:
        digits_only = "".join(ch for ch in clock if ch.isdigit())
        if digits_only:
            try:
                if int(digits_only) == 0:
                    return None
            except ValueError:
                # If conversion fails, keep the original formatted clock
                pass
    else:
        # If there are no digits and no alpha characters, treat as placeholder (e.g., '--')
        if not any(ch.isalpha() for ch in clock):
            return None

    return clock


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO8601 datetime string, returning an aware datetime in UTC."""
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _format_phase_label(league: Optional[str], period: Optional[str], short_detail: str) -> Optional[str]:
    """Format a human-friendly label for the current period/quarter/inning."""
    league_lower = (league or "").lower()
    period_str = str(period).strip() if period not in (None, "") else ""
    detail_lower = short_detail.lower() if short_detail else ""

    def _ordinal(n: int) -> str:
        suffix = "th"
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            if n % 10 == 1:
                suffix = "st"
            elif n % 10 == 2:
                suffix = "nd"
            elif n % 10 == 3:
                suffix = "rd"
        return f"{n}{suffix}"

    try:
        period_int = int(period_str)
    except (TypeError, ValueError):
        period_int = None

    if league_lower in {"nba", "wnba", "ncaam", "ncaaw", "basketball"}:
        if period_int is not None:
            if period_int <= 4:
                return f"Q{period_int}"
            overtime = period_int - 4
            return "OT" if overtime == 1 else f"{overtime}OT"

    if league_lower in {"nfl", "cfb", "college football", "football"}:
        if period_int is not None:
            if period_int <= 4:
                return f"Q{period_int}"
            overtime = period_int - 4
            return "OT" if overtime == 1 else f"{overtime}OT"

    if league_lower in {"nhl", "hockey"}:
        if period_int is not None:
            if period_int == 1:
                return "1st"
            if period_int == 2:
                return "2nd"
            if period_int == 3:
                return "3rd"
            overtime = period_int - 3
            return "OT" if overtime == 1 else f"{overtime}OT"

    if league_lower in {"mlb", "baseball"}:
        if short_detail:
            if detail_lower.startswith("bottom "):
                return short_detail.replace("Bottom ", "Bot ", 1)
            return short_detail
        if period_int is not None:
            return _ordinal(period_int)

    if short_detail:
        return short_detail

    if period_str:
        return f"Period {period_str}"

    return None


def _extract_team_keys(event: Dict) -> List[str]:
    """Build stable keys used to track a team's future schedule across events."""
    league = (event.get("league") or "").lower()
    team_keys: List[str] = []

    for side in ("home_team", "away_team"):
        team = event.get(side) or {}

        team_id = str(team.get("id") or "").strip()
        abbreviation = (team.get("abbreviation") or "").strip().lower()
        name = (team.get("name") or "").strip().lower()

        if team_id:
            team_keys.append(f"{league}::id::{team_id}")
        if abbreviation:
            team_keys.append(f"{league}::abbr::{abbreviation}")
        if name:
            team_keys.append(f"{league}::name::{name}")

    return team_keys


def _ensure_future_events_for_favorites(
    events: List[Dict],
    league: str,
    favorite_teams: Optional[List[str]],
    base_url: str,
    read_timeout: int,
) -> List[Dict]:
    """Augment the event list with upcoming games for favorites that are missing."""
    normalized_favorites, alias_lookup = _normalize_favorites_for_league(favorite_teams, league)
    if not normalized_favorites:
        return events

    now = datetime.now(timezone.utc)
    covered = set()
    for event in events:
        if event.get("status") != "scheduled":
            continue
        start = _parse_iso_datetime(event.get("start_time_utc") or event.get("start_time"))
        if not start or start < now:
            continue
        covered.update(_event_primary_matches(event, alias_lookup))

    missing = normalized_favorites - covered
    if not missing:
        return events

    seen_ids = {event.get("id") for event in events if event.get("id")}
    augmented_events = list(events)

    for day_offset in range(1, FUTURE_LOOKAHEAD_DAYS + 1):
        if not missing:
            break

        date_str = (now + timedelta(days=day_offset)).strftime("%Y%m%d")
        future_url = f"{base_url}?dates={date_str}"
        future_data = _make_request_with_backoff(future_url, timeout=read_timeout)
        if not future_data:
            continue

        future_processed = _process_espn_response(future_data, league)
        for future_event in future_processed["events"]:
            if future_event.get("id") in seen_ids or future_event.get("status") != "scheduled":
                continue

            start_time = _parse_iso_datetime(future_event.get("start_time_utc") or future_event.get("start_time"))
            if not start_time or start_time < now:
                continue

            matches = _event_primary_matches(future_event, alias_lookup)
            if matches & missing:
                augmented_events.append(future_event)
                seen_ids.add(future_event.get("id"))
                missing = missing - matches

        # If we're down to a single missing favorite, break early once covered
        if not missing:
            break

    if len(augmented_events) != len(events):
        augmented_events.sort(
            key=lambda evt: _parse_iso_datetime(evt.get("start_time_utc") or evt.get("start_time"))
            or datetime.max.replace(tzinfo=timezone.utc)
        )
        return augmented_events

    return events


def _filter_final_events_by_retention(events: List[Dict]) -> List[Dict]:
    """Remove final events that exceed retention windows or are eclipsed by upcoming games."""
    now = datetime.now(timezone.utc)

    # Track the next scheduled game start for each team
    team_next_game: Dict[str, datetime] = {}
    for event in events:
        if event.get("status") != "scheduled":
            continue

        start_time = _parse_iso_datetime(event.get("start_time_utc") or event.get("start_time"))
        if not start_time:
            continue

        for team_key in _extract_team_keys(event):
            existing = team_next_game.get(team_key)
            if existing is None or start_time < existing:
                team_next_game[team_key] = start_time

    filtered_events: List[Dict] = []
    for event in events:
        if event.get("status") != "final":
            filtered_events.append(event)
            continue

        event_start = _parse_iso_datetime(event.get("start_time_utc") or event.get("start_time"))

        # Determine if there's an upcoming game for either participating team
        team_keys = _extract_team_keys(event)
        relevant_next_games = [team_next_game[key] for key in team_keys if key in team_next_game]

        # Determine if the game should be kept based on retention rules
        should_keep = False

        if event_start:
            # Determine the date of the original game (in local timezone)
            try:
                game_date_local = event_start.astimezone(DISPLAY_TIMEZONE).date()
            except Exception:
                game_date_local = event_start.astimezone(timezone.utc).date()

            # Get "tomorrow" (the subsequent day after the game)
            game_day_after = game_date_local + timedelta(days=1)

            # Check if game started within last 24 hours (the max retention period)
            if now - event_start <= timedelta(hours=24):
                # Find next games that are on the day after the original game (game_day_after)
                next_day_games = [next_game for next_game in relevant_next_games if next_game.date() == game_day_after]

                if next_day_games:
                    # At least one team has a game the day after the original game,
                    # keep the score until 6 hours before the earliest game that day
                    earliest_next = min(next_day_games)
                    if now < earliest_next - timedelta(hours=6):
                        should_keep = True
                else:
                    # Neither team has a game the day after the original game,
                    # so keep the final score for the full 24 hours after start
                    should_keep = True
            else:
                # Older than 24 hours, don't keep
                should_keep = False

        if should_keep:
            filtered_events.append(event)

    return filtered_events


def _apply_consecutive_empty_metadata(result: Dict, previous_data: Optional[Dict]) -> None:
    """Update consecutive empty refresh metadata on the result payload."""
    games = result.get("games", [])
    meta = result.setdefault("meta", {})

    is_empty = len(games) == 0
    previous_count = 0

    if previous_data and isinstance(previous_data, dict):
        previous_meta = previous_data.get("meta") or {}
        previous_count = previous_meta.get("consecutive_empty_count", 0)

    consecutive_empty = previous_count + 1 if is_empty else 0
    meta["consecutive_empty_count"] = consecutive_empty
    meta["should_hide"] = consecutive_empty >= 3


def get_sports_ticker_data(
    favorite_teams: Optional[List[str]] = None,
    force_refresh: bool = False,
    allow_background_refresh: bool = True,
    cache_only: bool = False,
) -> Dict:
    """Get sports ticker data with the required contract for Phase 3."""
    from flask import current_app

    config = current_app.config.get("CONFIG")
    app = current_app._get_current_object()

    if favorite_teams is None:
        if config and hasattr(config, "providers"):
            sports_config = config.providers.get("sports", {})
            favorite_teams = sports_config.get("favorite_teams", [])
        else:
            favorite_teams = []
    favorite_teams = list(favorite_teams or [])

    # Try to get from file cache first
    cached_payload_raw = _read_cache_file()
    prepared_cache = _prepare_cached_payload(cached_payload_raw, favorite_teams) if cached_payload_raw else None
    cache_is_stale = prepared_cache.get("meta", {}).get("stale", False) if prepared_cache else False

    if cache_only:
        if prepared_cache:
            if cache_is_stale and allow_background_refresh:
                _trigger_background_refresh(app, favorite_teams)
            return prepared_cache

        placeholder = _build_placeholder_payload(favorite_teams)
        if allow_background_refresh:
            _trigger_background_refresh(app, favorite_teams)
        return placeholder

    if prepared_cache and not force_refresh:
        # Return cached payload immediately; if stale, refresh asynchronously
        if cache_is_stale and allow_background_refresh:
            _trigger_background_refresh(app, favorite_teams)
        return prepared_cache

    # No cache available and not forcing refresh: return fast placeholder and refresh in background
    if prepared_cache is None and not force_refresh:
        placeholder = _build_placeholder_payload(favorite_teams)
        if allow_background_refresh:
            _trigger_background_refresh(app, favorite_teams)
        return placeholder

    # Get configuration values
    enabled_leagues = []
    timeout_thresholds = {"connect": 5, "read": 10}

    if config and hasattr(config, "providers"):
        sports_config = config.providers.get("sports", {})
        enabled_leagues = sports_config.get("enabled_leagues", ["nba", "nfl", "mlb", "nhl"])
        timeout_thresholds = sports_config.get("timeout_thresholds", timeout_thresholds)

    if not enabled_leagues:
        enabled_leagues = ["nba", "nfl", "mlb", "nhl"]
    else:
        # Preserve original order while removing duplicates
        enabled_leagues = list(dict.fromkeys(enabled_leagues))

    # If not in cache, fetch from ESPN with resilience
    try:
        # Fetch data from all enabled leagues in parallel to cap wall-clock time
        all_games: List[Dict] = []
        with ThreadPoolExecutor(max_workers=min(4, len(enabled_leagues) or 1)) as executor:
            future_map = {
                executor.submit(
                    fetch_sports_data_with_resilience,
                    app,
                    league,
                    favorite_teams=favorite_teams,
                    timeout_thresholds=timeout_thresholds,
                ): league
                for league in enabled_leagues
            }
            try:
                for future in as_completed(future_map, timeout=25):
                    league = future_map[future]
                    try:
                        league_data = future.result()
                        if league_data:
                            all_games.extend(league_data.get("events", []))
                    except Exception as exc:
                        logging.warning(f"League fetch failed for {league}: {exc}")
            except FuturesTimeoutError:
                logging.warning(
                    "ESPN fetch timed out after 25s; cancelling remaining futures and using partial results"
                )
                for future in future_map:
                    future.cancel()

        # Create result with proper metadata
        result = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "meta": {
                "timezone": "UTC",
                "cache_age_seconds": 0,
                "stale": False,
                "favorites": favorite_teams,
                "source": "espn-scoreboard-v1",
                "fetch_error_reason": None,
            },
            "games": all_games,
        }
        result = _prepare_cached_payload(result, favorite_teams)
        _apply_consecutive_empty_metadata(result, prepared_cache)
        result["meta"]["fetch_error_reason"] = None

        # Write to file cache using atomic write
        success = _atomic_write_cache_file(_get_cache_file_path(), result)
        if not success:
            logging.error("Failed to write sports ticker data to file cache")

        return result
    except Exception as e:
        logging.error(f"Error fetching sports ticker data: {e}")
        # Check if we have a fallback cached version
        fallback_data = prepared_cache
        if fallback_data:
            # Mark as stale and update error reason
            fallback_meta = fallback_data.setdefault("meta", {})
            fallback_meta["stale"] = True
            fallback_meta["fetch_error_reason"] = str(e)
            return fallback_data
        else:
            # Return an empty data structure that conforms to the contract
            error_payload = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "meta": {
                    "timezone": "UTC",
                    "cache_age_seconds": 0,
                    "stale": True,
                    "favorites": favorite_teams,
                    "source": "espn-scoreboard-v1",
                    "fetch_error_reason": str(e),
                    "consecutive_empty_count": 1,
                    "should_hide": False,
                },
                "games": [],
            }
            error_payload = _prepare_cached_payload(error_payload, favorite_teams)
            error_payload["meta"]["stale"] = True
            error_payload["meta"]["fetch_error_reason"] = str(e)
            _apply_consecutive_empty_metadata(error_payload, prepared_cache)
            # Write error result to cache
            _atomic_write_cache_file(_get_cache_file_path(), error_payload)
            return error_payload


def transform_to_ticker_contract(sports_data: SportsData, favorite_teams: List[str]) -> Dict:
    """Transform the standard sports data to the ticker contract required by Phase 2."""
    games = []

    for game in sports_data.games:
        # Transform the game to match the required ticker contract
        transformed_game = {
            "id": game.id,
            "league": "NBA",  # Default to NBA for now; this should be determined by source
            "status": game.status,
            "start_time": game.start_time.isoformat() if game.start_time else None,
            "start_time_utc": game.start_time.isoformat() if game.start_time else None,
            "time_remaining": game.time_remaining,
            "quarter": game.quarter,
            "home_team": {
                "name": game.home_team.name,
                "abbreviation": game.home_team.abbreviation or game.home_team.name[:3],
                "score": game.home_score,
            },
            "away_team": {
                "name": game.away_team.name,
                "abbreviation": game.away_team.abbreviation or game.away_team.name[:3],
                "score": game.away_score,
            },
            "home_score": game.home_score,
            "away_score": game.away_score,
            "broadcast": game.broadcast,
            "source_url": f"https://www.espn.com/game/_/gameId/{game.id}" if game.id else None,
        }
        games.append(transformed_game)

    # Calculate cache age (time since last update)
    last_updated = sports_data.last_updated if sports_data.last_updated else datetime.now(timezone.utc)
    cache_age_seconds = int((datetime.now(timezone.utc) - last_updated).total_seconds())

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "timezone": "UTC",
            "cache_age_seconds": cache_age_seconds,
            "stale": cache_age_seconds > 120,  # Flag as stale if older than 2 minutes
            "favorites": favorite_teams,
            "source": sports_data.source,
            "fetch_error_reason": None,
        },
        "games": games,
    }


def refresh_sports_ticker_data() -> bool:
    """Force refresh sports ticker data by rotating cache files and fetching fresh data."""
    global FETCH_COUNT, FETCH_LATENCY_METRICS, CACHE_HIT_COUNT, CACHE_MISS_COUNT, CACHE_WRITE_DURATION_METRICS

    try:
        from flask import current_app

        config = current_app.config.get("CONFIG")
        if config and hasattr(config, "providers"):
            sports_config = config.providers.get("sports", {})
            favorite_teams = sports_config.get("favorite_teams", [])
        else:
            favorite_teams = []

        # Rotate existing cache before overwriting so we always keep a backup of the previous good data
        _rotate_cache_files()
        # Fetch fresh data to populate main cache file (this will handle the consecutive empty logic)
        get_sports_ticker_data(favorite_teams, force_refresh=True)
        return True
    except Exception as e:
        logging.error(f"Error refreshing sports ticker data: {e}")
        return False


def _make_request_with_backoff(url: str, timeout: int = 8, max_attempts: int = 2) -> Optional[Dict]:
    """Make a request to ESPN API with exponential backoff and retry logic."""
    global FETCH_COUNT, FETCH_LATENCY_METRICS

    start_time = time.time()
    for attempt in range(1, max_attempts + 1):
        try:
            # Use the timeout as both connect and read timeout
            response = rate_limited_get(url, timeout=(timeout, timeout), service_name="sports_ticker")

            fetch_duration = time.time() - start_time
            FETCH_LATENCY_METRICS.append(fetch_duration)
            FETCH_COUNT += 1

            # Keep only the latest 100 metrics to prevent memory bloat
            if len(FETCH_LATENCY_METRICS) > 100:
                FETCH_LATENCY_METRICS = FETCH_LATENCY_METRICS[-100:]

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limited
                # Calculate sleep time with tight backoff to avoid long stalls
                base_delay = 0.5
                sleep_time = min(6, base_delay * (2 ** (attempt - 1)) * (0.5 + random.random()))  # nosec B311
                logging.warning(
                    f"Rate limited (429) for {url}, sleeping for {sleep_time:.2f}s (attempt {attempt}/{max_attempts})"
                )
                time.sleep(sleep_time)
            else:
                # For other HTTP errors, also use backoff but with shorter delays
                base_delay = 0.5
                sleep_time = min(6, base_delay * (2 ** (attempt - 1)) * (0.5 + random.random()))  # nosec B311
                logging.warning(
                    f"HTTP {response.status_code} for {url}, sleeping for {sleep_time:.2f}s (attempt {attempt}/{max_attempts})"
                )
                time.sleep(sleep_time)

        except RateLimitError:
            fetch_duration = time.time() - start_time
            FETCH_LATENCY_METRICS.append(fetch_duration)
            FETCH_COUNT += 1
            if len(FETCH_LATENCY_METRICS) > 100:
                FETCH_LATENCY_METRICS = FETCH_LATENCY_METRICS[-100:]
            base_delay = 0.5
            sleep_time = min(6, base_delay * (2 ** (attempt - 1)) * (0.5 + random.random()))  # nosec B311
            logging.warning(
                "Rate limited for %s, sleeping for %.2fs (attempt %s/%s)",
                url,
                sleep_time,
                attempt,
                max_attempts,
            )
            time.sleep(sleep_time)
        except requests.exceptions.Timeout:
            fetch_duration = time.time() - start_time
            FETCH_LATENCY_METRICS.append(fetch_duration)
            FETCH_COUNT += 1

            # Keep only the latest 100 metrics to prevent memory bloat
            if len(FETCH_LATENCY_METRICS) > 100:
                FETCH_LATENCY_METRICS = FETCH_LATENCY_METRICS[-100:]

            logging.warning(f"Timeout for {url}, attempt {attempt}/{max_attempts}")
            if attempt == max_attempts:
                logging.error(f"Max attempts reached for {url} due to timeouts")
                return None
            base_delay = 0.75
            sleep_time = min(8, base_delay * (2 ** (attempt - 1)) * (0.5 + random.random()))  # nosec B311
            time.sleep(sleep_time)
        except requests.exceptions.RequestException as e:
            fetch_duration = time.time() - start_time
            FETCH_LATENCY_METRICS.append(fetch_duration)
            FETCH_COUNT += 1

            # Keep only the latest 100 metrics to prevent memory bloat
            if len(FETCH_LATENCY_METRICS) > 100:
                FETCH_LATENCY_METRICS = FETCH_LATENCY_METRICS[-100:]

            logging.warning(f"Request error for {url}: {e}, attempt {attempt}/{max_attempts}")
            if attempt == max_attempts:
                logging.error(f"Max attempts reached for {url} due to request errors")
                return None
            base_delay = 0.5
            sleep_time = min(6, base_delay * (2 ** (attempt - 1)) * (0.5 + random.random()))  # nosec B311
            time.sleep(sleep_time)

    return None


def fetch_sports_data_with_resilience(
    app=None,
    league: str = "nba",
    favorite_teams: Optional[List[str]] = None,
    timeout_thresholds: Optional[Dict] = None,
) -> Optional[Dict]:
    """Fetch sports data from ESPN with resilience patterns."""
    if isinstance(app, str):
        league = app
        app = None

    if app is None and has_app_context():
        app = current_app._get_current_object()

    config = None
    if app is not None:
        with app.app_context():
            config = current_app.config.get("CONFIG")

    # Get configured endpoints from config, fallback to defaults
    endpoints = {
        "nba": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
        "nfl": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
        "mlb": "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
        "nhl": "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
    }

    if config and hasattr(config, "providers"):
        sports_config = config.providers.get("sports", {})
        configured_endpoints = sports_config.get("scoreboard_endpoints", {})
        endpoints.update(configured_endpoints)  # Override defaults with configured values

    if league not in endpoints:
        logging.warning(f"Unsupported league: {league}, defaulting to NBA")
        league = "nba"

    url = endpoints[league]
    try:
        today_local = datetime.now(DISPLAY_TIMEZONE)
    except Exception:
        today_local = datetime.now(timezone.utc)
    scoreboard_date = today_local.strftime("%Y%m%d")
    date_param = f"dates={scoreboard_date}"
    url_with_date = f"{url}?{date_param}" if "?" not in url else f"{url}&{date_param}"

    # Use provided timeout thresholds or defaults
    if timeout_thresholds is None:
        timeout_thresholds = {"connect": 5, "read": 10}

    connect_timeout = timeout_thresholds.get("connect", 5)
    read_timeout = timeout_thresholds.get("read", 10)
    _ = (connect_timeout, read_timeout)  # keep for future per-request tuning

    try:
        data = _make_request_with_backoff(url_with_date, timeout=read_timeout)
        if data:
            # Process the ESPN data to normalize statuses and ensure stable IDs
            processed_data = _process_espn_response(data, league)
            events = processed_data.get("events", [])
            events = _ensure_future_events_for_favorites(events, league, favorite_teams, url, read_timeout)
            processed_data["events"] = _filter_final_events_by_retention(events)
            return processed_data
    except Exception as e:
        logging.error(f"Error fetching sports data for {league}: {e}")

    return None


def _process_espn_response(data: Dict, league: str) -> Dict:
    """Process ESPN API response to normalize data according to the ticker contract."""
    processed_events = []

    events = data.get("events", [])
    for event in events:
        # Normalize status
        status_raw = event.get("status", {}).get("type", {}).get("name", "STATUS_UNKNOWN")
        status = _normalize_status(status_raw)

        # Get competition data
        competition = event.get("competitions", [{}])[0] if event.get("competitions") else {}

        # Extract teams and scores
        home_team_data = None
        away_team_data = None
        home_score = None
        away_score = None

        competitors = competition.get("competitors", [])
        for competitor in competitors:
            team_data = competitor.get("team", {}) or {}
            score_raw = competitor.get("score")
            try:
                score_value = int(score_raw) if score_raw not in (None, "") else None
            except (TypeError, ValueError):
                score_value = None

            if competitor.get("homeAway") == "home":
                home_team_data = team_data
                home_score = score_value
            elif competitor.get("homeAway") == "away":
                away_team_data = team_data
                away_score = score_value

        # Process start time
        start_time = None
        start_time_utc = None
        date_str = event.get("date")
        if date_str:
            try:
                start_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                start_time_utc = start_time
            except ValueError:
                logging.warning(f"Could not parse date: {date_str}")

        # Process game clock info
        status_info = competition.get("status", {}) if competition else {}
        status_type = status_info.get("type", {}) if status_info else {}
        state = status_type.get("state", "")
        state_lower = state.lower() if isinstance(state, str) else ""
        raw_clock = status_info.get("displayClock")
        time_remaining = _normalize_display_clock(raw_clock)
        raw_period = status_info.get("period", None)
        short_detail = status_type.get("shortDetail", "") if status_type else ""
        if isinstance(short_detail, str):
            short_detail = short_detail.strip()
        else:
            short_detail = ""

        phase_label = _format_phase_label(league, raw_period, short_detail)

        if status == "scheduled":
            phase_label = None
        elif status == "final":
            phase_label = phase_label or short_detail or "Final"

        # Determine live status overrides
        phase_hint_source = phase_label or short_detail
        has_clock_hint = bool(time_remaining) or (
            phase_hint_source
            and any(
                token in phase_hint_source.lower()
                for token in (
                    "q",
                    "half",
                    "inning",
                    "period",
                    "quarter",
                    "top",
                    "bottom",
                    "ot",
                    "overtime",
                    "1st",
                    "2nd",
                    "3rd",
                )
            )
        )
        positive_scores = any((score or 0) > 0 for score in (home_score, away_score))

        if status == "scheduled":
            if state_lower == "in":
                status = "in_progress"
            elif state_lower == "post":
                status = "final"
            elif (has_clock_hint or positive_scores) and state_lower not in ("pre", ""):
                status = "in_progress"
            else:
                # Hide placeholder zeros for games that have not started
                home_score = None if home_score in (0, None) else home_score
                away_score = None if away_score in (0, None) else away_score

        home_team_data = home_team_data or {}
        away_team_data = away_team_data or {}

        clock_display: Optional[str]
        if status == "in_progress":
            if time_remaining and phase_label and time_remaining.lower() != phase_label.lower():
                clock_display = f"{time_remaining} {phase_label}"
            else:
                clock_display = time_remaining or phase_label or short_detail or None
        else:
            clock_display = None

        processed_event = {
            "id": event.get("id", ""),
            "league": league.upper(),
            "status": status,
            "start_time": start_time.isoformat() if start_time else None,
            "start_time_utc": start_time_utc.isoformat() if start_time_utc else None,
            "time_remaining": clock_display,
            "quarter": phase_label if phase_label else None,
            "home_team": {
                "id": home_team_data.get("id"),
                "name": home_team_data.get("displayName", ""),
                "abbreviation": home_team_data.get("abbreviation", ""),
                "score": home_score,
            },
            "away_team": {
                "id": away_team_data.get("id"),
                "name": away_team_data.get("displayName", ""),
                "abbreviation": away_team_data.get("abbreviation", ""),
                "score": away_score,
            },
            "home_score": home_score,
            "away_score": away_score,
            "broadcast": None,  # ESPN doesn't typically provide this via the public API
            "source_url": event.get("links", [{}])[0].get("href") if event.get("links") else None,
        }

        processed_events.append(processed_event)

    return {"updated_at": datetime.now(timezone.utc).isoformat(), "events": processed_events}


def _normalize_status(status_raw: str) -> str:
    """Normalize ESPN status strings to the standard ticker format."""
    status_raw_lower = status_raw.lower()

    if any(token in status_raw_lower for token in ("completed", "final", "closed", "closing")):
        return "final"
    if any(
        token in status_raw_lower
        for token in ("in_progress", "in progress", "inprogress", "live", "in_countdown", "in countdown")
    ):
        return "in_progress"
    if any(token in status_raw_lower for token in ("scheduled", "pre", "tbd")):
        return "scheduled"

    # Default to scheduled for unknown statuses
    return "scheduled"


def get_polling_interval(games: List[Dict], favorite_teams: List[str], polling_defaults: Dict[str, int]) -> int:
    """Determine the appropriate polling interval based on game states and favorite teams."""
    now = datetime.now(timezone.utc)

    # Check if any favorite team has a live game
    for game in games:
        # Check if this is a favorite team game
        home_team_name = game.get("home_team", {}).get("name", "").lower()
        away_team_name = game.get("away_team", {}).get("name", "").lower()
        home_team_abbr = game.get("home_team", {}).get("abbreviation", "").lower()
        away_team_abbr = game.get("away_team", {}).get("abbreviation", "").lower()

        is_favorite_game = any(
            fav_team.lower() in [home_team_name, away_team_name, home_team_abbr, away_team_abbr]
            for fav_team in favorite_teams
        )

        if is_favorite_game:
            status = game.get("status", "scheduled")

            # Live favorite games: 90 seconds
            if status == "in_progress":
                return polling_defaults.get("active", 90)  # 90 seconds as per Phase 3

            # Scheduled favorite games (within next 30 min): 300 seconds (5 min) instead of 30 min to make it more responsive
            if status == "scheduled":
                start_time_str = game.get("start_time_utc")
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                        time_to_game = (start_time - now).total_seconds()
                        # If game starts within 60 minutes, poll more frequently
                        if 0 <= time_to_game <= 3600:  # 1 hour
                            return polling_defaults.get("idle", 300)  # 5 minutes during pre-game
                    except Exception:  # nosec B110
                        pass

            # Final favorite games: 150 seconds (2.5 min) instead of 15 min to make it more responsive
            if status == "final":
                return polling_defaults.get("post_final", 150)  # 2.5 minutes after final

    # Default to idle interval (close to 30 minutes as per Phase 3 - using 1800 seconds)
    return polling_defaults.get("idle", 1800)


def get_available_leagues() -> List[Dict[str, str]]:
    """Get the available leagues that can be used for ticker data."""
    return [
        {"id": "nba", "name": "NBA"},
        {"id": "nfl", "name": "NFL"},
        {"id": "mlb", "name": "MLB"},
        {"id": "nhl", "name": "NHL"},
    ]


def get_sports_ticker_metrics() -> Dict[str, any]:
    """Get metrics for the sports ticker service."""
    global FETCH_COUNT, FETCH_LATENCY_METRICS, CACHE_HIT_COUNT, CACHE_MISS_COUNT, CACHE_WRITE_DURATION_METRICS

    total_cache_requests = CACHE_HIT_COUNT + CACHE_MISS_COUNT

    cache_hit_rate = (CACHE_HIT_COUNT / total_cache_requests * 100) if total_cache_requests > 0 else 0
    avg_fetch_latency = sum(FETCH_LATENCY_METRICS) / len(FETCH_LATENCY_METRICS) if FETCH_LATENCY_METRICS else 0
    avg_cache_write_duration = (
        sum(CACHE_WRITE_DURATION_METRICS) / len(CACHE_WRITE_DURATION_METRICS) if CACHE_WRITE_DURATION_METRICS else 0
    )

    return {
        "fetch_count": FETCH_COUNT,
        "fetch_latency_avg_seconds": round(avg_fetch_latency, 3),
        "fetch_latency_max_seconds": max(FETCH_LATENCY_METRICS) if FETCH_LATENCY_METRICS else 0,
        "fetch_latency_min_seconds": min(FETCH_LATENCY_METRICS) if FETCH_LATENCY_METRICS else 0,
        "cache_hit_count": CACHE_HIT_COUNT,
        "cache_miss_count": CACHE_MISS_COUNT,
        "cache_hit_rate_percent": round(cache_hit_rate, 2),
        "cache_write_duration_avg_seconds": round(avg_cache_write_duration, 3),
        "total_cache_requests": total_cache_requests,
    }
