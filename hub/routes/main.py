import json
import os
import platform
from datetime import datetime

import requests
from flask import current_app, g, jsonify, render_template, request

from hub.data.team_catalog import TEAM_CATALOG, get_normalized_league
from hub.integrations import spotify_auth
from hub.services import calendar
from hub.utils.auth import generate_media_launcher_token
from hub.utils.config_helpers import get_config_dict

from . import main_bp


def get_serialized_public_config(config):
    """
    Get or create cached serialized public config to avoid double encoding.
    """
    if hasattr(g, "public_config_json"):
        return g.public_config_json

    # Convert Pydantic model to dictionary for serialization
    config_dict = get_config_dict(config)

    # Create public config with only safe, UI-relevant fields
    public_config = {
        "layout": config_dict.get("layout", {}),
        "apps": config_dict.get("apps", []),
        "extra_apps": config_dict.get("extra_apps", []),
        "local_apps": config_dict.get("local_apps", []),
        "features": {
            "voice": config_dict.get("features", {}).get("voice", False),
            "voice_wake_word": config_dict.get("features", {}).get("voice_wake_word"),
            "kiosk": config_dict.get("features", {}).get("kiosk", True),
            "auth": config_dict.get("features", {}).get("auth", False),
            "plugins": config_dict.get("features", {}).get("plugins", False),
            "sports_ticker_clickable": config_dict.get("features", {}).get("sports_ticker_clickable", False),
            "sports_ticker_enabled": config_dict.get("features", {}).get("sports_ticker_enabled", True),
            "sports_ticker_mock_mode": config_dict.get("features", {}).get("sports_ticker_mock_mode", False),
        },
        "ui": {
            "theme": config_dict.get("ui", {}).get("theme", "auto"),
            "density": config_dict.get("ui", {}).get("density", "comfortable"),
            "burn_in": config_dict.get("ui", {}).get("burn_in", {}),
        },
        "photos": {
            "enabled": config_dict.get("photos", {}).get("enabled", False),
            "slideshow_interval": config_dict.get("photos", {}).get("slideshow_interval", 5),
        },
        "chores": {
            "enabled": config_dict.get("chores", {}).get("enabled", False),
        },
        "music": {
            "enabled": config_dict.get("music", {}).get("enabled", True),
        },
        "news": {
            "enabled": config_dict.get("news", {}).get("enabled", True),
        },
    }

    # Add providers config (only non-sensitive parts)
    providers_config = config_dict.get("providers", {})
    if providers_config:
        sanitized_providers = {}

        # Sanitize calendar provider (only kind, not credentials)
        if "calendar" in providers_config:
            calendar_config = providers_config["calendar"]
            if isinstance(calendar_config, dict):
                sanitized_providers["calendar"] = {
                    "kind": calendar_config.get("kind", "ics"),
                    "ics_url": calendar_config.get("ics_url"),
                }

        # Sanitize weather provider (only kind, not credentials)
        if "weather" in providers_config:
            weather_config = providers_config["weather"]
            if isinstance(weather_config, dict):
                sanitized_providers["weather"] = {
                    "kind": weather_config.get("kind", "open_meteo"),
                    "location": weather_config.get("location", {}),
                }

        # Sanitize sports provider (only non-sensitive parts like favorite teams, not API keys)
        if "sports" in providers_config:
            sports_config = providers_config["sports"]
            if isinstance(sports_config, dict):
                sanitized_providers["sports"] = {
                    "kind": sports_config.get("kind", "espn"),
                    "favorite_teams": sports_config.get("favorite_teams", []),
                    "enabled_leagues": sports_config.get("enabled_leagues", ["nba", "nfl", "mlb", "nhl"]),
                }

        # Sanitize homeassistant provider (only base URL, not credentials)
        if "homeassistant" in providers_config:
            ha_config = providers_config["homeassistant"]
            if isinstance(ha_config, dict):
                sanitized_providers["homeassistant"] = {"base_url": ha_config.get("base_url")}

        public_config["providers"] = sanitized_providers

    # Add casting config if it exists (only non-sensitive parts)
    casting_config = config_dict.get("casting", {})
    if casting_config:
        public_config["casting"] = {
            "enabled": casting_config.get("enabled", False),
            "discovery_enabled": casting_config.get("discovery_enabled", True),
            "default_volume": casting_config.get("default_volume", 50),
        }

    # Add security config (only non-sensitive parts)
    security_config = config_dict.get("security", {})
    if security_config:
        public_config["security"] = {
            "ssl_enabled": security_config.get("ssl_enabled", False),
            "rate_limit_enabled": security_config.get("rate_limit_enabled", True),
            "ip_whitelist_enabled": security_config.get("ip_whitelist_enabled", False),
            "session_timeout": security_config.get("session_timeout", 3600),
            "secure_headers": security_config.get("secure_headers", True),
            "admin_enabled": security_config.get("admin_enabled", False),
        }

    # The browser needs display timing only. Addresses and provider credentials stay server-side.
    commute_config = config_dict.get("commute", {})
    if commute_config:
        public_config["commute"] = {
            "enabled": commute_config.get("enabled", False),
            "always_visible": commute_config.get("always_visible", False),
            "morning_window": commute_config.get("morning_window", {"start": "06:00", "end": "09:00"}),
            "evening_window": commute_config.get("evening_window", {"start": "16:30", "end": "18:30"}),
            "refresh_minutes": commute_config.get("refresh_minutes", 5),
        }

    # Add media launcher config (allowed_domains drives the client-side whitelist)
    media_config = config_dict.get("media", {})
    if media_config:
        public_config["media"] = {
            "enabled": media_config.get("enabled", True),
            "launcher_endpoint": media_config.get("launcher_endpoint", "http://127.0.0.1:7666/v1/open_media"),
            "allowed_domains": media_config.get("allowed_domains", []),
        }

    # Cache the serialized public config to avoid double encoding
    serialized_config = json.dumps(public_config)
    setattr(g, "public_config_json", serialized_config)
    return serialized_config


def _get_media_launcher_token() -> str:
    ttl_seconds = int(os.environ.get("MEDIA_LAUNCHER_TOKEN_TTL", "300"))
    return generate_media_launcher_token(ttl_seconds=ttl_seconds)


@main_bp.app_context_processor
def inject_media_launcher_token():
    return {"media_launcher_token": _get_media_launcher_token()}


def build_public_config(config):
    """
    Create a sanitized public config that excludes sensitive data.
    This function strips secrets like provider credentials, webhook URLs, API keys,
    and only keeps UI-relevant configuration.
    """
    if not config:
        return {}

    # Use cached public config if available in this request context
    if hasattr(g, "public_config_json"):
        return json.loads(g.public_config_json)

    # Use the same logic as get_serialized_public_config to create the config
    # This will also cache it for future use
    get_serialized_public_config(config)
    return json.loads(g.public_config_json)


@main_bp.route("/media_control")
def media_control():
    """Tiny controller overlay opened as a child Chrome window alongside a media app."""
    from flask import make_response as _make_response
    html = """<!doctype html>
<html>
<head>
  <style>
    body { margin:0; background:transparent; }
    #ctrl { position: fixed; left:8px; top:8px; z-index:9999; }
    button { font-size:18px; padding:8px 12px; border-radius:6px;
             background: rgba(0,0,0,0.7); color: white;
             border: 1px solid white; cursor: pointer; }
    button:hover { background: rgba(50,50,50,0.9); }
  </style>
</head>
<body>
  <div id="ctrl">
    <button id="closeBtn">&#x21ba; Home</button>
  </div>
  <script>
    document.getElementById('closeBtn').addEventListener('click', async () => {
      try {
        await fetch('/api/media/close', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
      } catch(err) {
        console.error('Failed to close media:', err);
      }
      try { window.close(); } catch(e){}
    });
  </script>
</body>
</html>"""
    resp = _make_response(html)
    resp.content_type = "text/html"
    return resp


@main_bp.route("/")
def index():
    """Main dashboard view."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("base.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/view/<name>")
def view(name):
    """Switch central view (calendar, media, etc.)"""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("base.html", config=public_config, config_json=serialized_public_config, active_view=name)


@main_bp.route("/view/cooking")
def cooking_view():
    """Cooking mode view with spotlighted media and recipe."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    from hub.services import timers

    active_timers = timers.list_active_timers()
    return render_template(
        "partials/cooking_mode.html",
        config=public_config,
        config_json=serialized_public_config,
        active_timers=active_timers,
    )


@main_bp.route("/view/sports")
def sports_view():
    """Sports view with detailed sports information."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    from hub.services import sports

    sports_data = sports.get_sports_data()
    from hub.utils.config_helpers import get_favorite_teams_from_config

    favorite_teams = get_favorite_teams_from_config(config)
    return render_template(
        "partials/sports_view.html",
        config=public_config,
        config_json=serialized_public_config,
        sports_data=sports_data,
        favorite_teams=favorite_teams,
    )


def _build_settings_context(config_obj):
    """Construct context for the settings view."""
    public_config = build_public_config(config_obj)

    from hub.utils.config_helpers import get_favorite_teams_from_config

    favorite_teams = get_favorite_teams_from_config(config_obj)

    catalog = {}
    for league_id, league in TEAM_CATALOG.items():
        normalized = get_normalized_league(league_id)
        if normalized:
            catalog[league_id] = normalized

    return {
        "config": public_config,
        "team_catalog": catalog,
        "favorite_teams": [team.lower() for team in favorite_teams or []],
    }


@main_bp.route("/partials/settings")
def settings_partial():
    """Settings partial view for user customization."""
    config = current_app.config.get("CONFIG", {})
    context = _build_settings_context(config)
    return render_template("partials/settings_view.html", **context)


@main_bp.route("/settings")
def settings_page():
    """Full settings page view."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    context = _build_settings_context(config)
    settings_html = render_template("partials/settings_view.html", **context)
    return render_template(
        "base.html",
        config=public_config,
        config_json=serialized_public_config,
        active_view="settings",
        settings_content=settings_html,
    )


@main_bp.route("/view/music")
def music_view():
    """Music view with player."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("partials/music_player.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/view/albums")
def albums_view():
    """Albums view."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("partials/photo_albums.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/view/ambient")
def ambient_view():
    """Ambient display view."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    # For ambient view, we might want to immediately activate ambient mode
    # But for now, we'll just return the base template which has the ambient functionality built-in
    return render_template(
        "base.html", config=public_config, config_json=serialized_public_config, active_view="ambient"
    )


@main_bp.route("/api/commute")
def commute_data():
    """Fetch Mapbox traffic server-side without disclosing household locations or tokens."""
    config = get_config_dict(current_app.config.get("CONFIG", {})).get("commute", {})
    if not config.get("enabled"):
        return jsonify({"error": "Commute is disabled."}), 404
    if config.get("provider", "mapbox").lower() != "mapbox":
        return jsonify({"error": "Only the Mapbox commute provider is supported."}), 400

    token = config.get("mapbox_token")
    home = str(config.get("home_address") or "").strip()
    work = str(config.get("work_address") or "").strip()
    if not token or not home or not work:
        return jsonify({"error": "Commute provider is not configured."}), 503

    commute_window = request.args.get("window", "morning")
    origin, destination = (work, home) if commute_window == "evening" else (home, work)
    try:
        coordinates = []
        for address in (origin, destination):
            response = requests.get(
                f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(address, safe='')}.json",
                params={"limit": 1, "access_token": token},
                timeout=10,
            )
            response.raise_for_status()
            features = response.json().get("features", [])
            if not features:
                return jsonify({"error": "A commute location could not be resolved."}), 502
            coordinates.append(features[0]["center"])
        route_response = requests.get(
            "https://api.mapbox.com/directions/v5/mapbox/driving-traffic/"
            + ";".join(f"{lng},{lat}" for lng, lat in coordinates),
            params={
                "alternatives": "false",
                "annotations": "congestion,closure",
                # Mapbox requires a full route overview when annotations are requested.
                "overview": "full",
                "access_token": token,
            },
            timeout=10,
        )
        route_response.raise_for_status()
        routes = route_response.json().get("routes", [])
        if not routes:
            return jsonify({"error": "No commute route was available."}), 502
        route = routes[0]
        has_incident = bool(route.get("incidents"))
        for leg in route.get("legs") or []:
            has_incident = has_incident or bool(leg.get("incidents"))
            closures = (leg.get("annotation") or {}).get("closure") or []
            has_incident = has_incident or any(bool(value) for value in closures)
        return jsonify({
            "eta_minutes": round(route["duration"] / 60) if route.get("duration") is not None else None,
            "typical_minutes": round(route["duration_typical"] / 60) if route.get("duration_typical") is not None else None,
            "has_incident": has_incident,
            "updated_at": datetime.now().isoformat(),
        })
    except (requests.RequestException, KeyError, TypeError, ValueError):
        # Requests exceptions can embed the full URL, including encoded household
        # addresses and access tokens. Keep the operational signal generic.
        current_app.logger.warning("Commute provider request failed; sensitive request details suppressed")
        return jsonify({"error": "Commute traffic is temporarily unavailable."}), 502


@main_bp.route("/partials/commute-map")
def commute_map_partial():
    """Return the commute map widget partial."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("partials/commute_map.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/partials/miniplayer")
def miniplayer_partial():
    """Return the miniplayer partial."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("partials/miniplayer.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/partials/center-zone")
def center_zone_partial():
    """Return the center zone partial with timers/notes/shopping or fallback."""
    from hub.services import notes as notes_service
    from hub.services import shopping as shopping_service

    last_updated = datetime.now().strftime("%I:%M %p").lstrip("0")
    mode = "fallback"
    notes = []
    shopping_items = []

    try:
        notes = notes_service.list_notes()[:3]
    except Exception:
        notes = []

    try:
        shopping_items = [item for item in shopping_service.list_shopping_items() if not item.done][:5]
    except Exception:
        shopping_items = []

    if notes or shopping_items:
        mode = "preview"

    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template(
        "partials/center_zone.html",
        config=public_config,
        config_json=serialized_public_config,
        mode=mode,
        notes=notes,
        shopping=shopping_items,
        last_updated=last_updated,
    )


@main_bp.route("/partials/casting")
def casting_modal():
    """Return the casting devices modal."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("partials/casting_modal.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/integrations/spotify/callback")
def spotify_callback():
    """Handle callbacks from Spotify's Authorization Code Flow with PKCE."""
    error = request.args.get("error")
    code = request.args.get("code")
    state = request.args.get("state")
    status = {"success": False, "message": ""}

    if error:
        status["message"] = f"Spotify authorization failed: {error}"
    elif not code or not state:
        status["message"] = "Missing authorization code or state."
    else:
        try:
            spotify_auth.finish_authorization(code, state)
            status["success"] = True
            status["message"] = "Spotify account connected. You can close this window."
        except spotify_auth.SpotifyAuthError as exc:
            status["message"] = str(exc)
        except Exception:
            current_app.logger.exception("Unexpected error handling Spotify callback")
            status["message"] = "Unexpected error while connecting to Spotify. Please try again."

    return render_template("integrations/spotify_callback.html", status=status)


@main_bp.route("/partials/calendar/add-event-modal")
def calendar_add_event_modal():
    """Return the add event modal partial."""
    config = current_app.config.get("CONFIG")
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    calendar_options = calendar.get_configured_calendar_options()
    default_calendar_selection = None
    for option in calendar_options:
        value = option.get("value") if isinstance(option, dict) else None
        if value == "google:primary":
            default_calendar_selection = value
            break
        if value and value.startswith("google:") and default_calendar_selection is None:
            default_calendar_selection = value
    return render_template(
        "partials/calendar_add_event_modal.html",
        config=public_config,
        config_json=serialized_public_config,
        calendar_options=calendar_options,
        default_calendar_selection=default_calendar_selection,
    )


@main_bp.route("/partials/notes-modal")
def notes_modal():
    """Return the notes modal partial."""
    from hub.services import notes as notes_service

    all_notes = notes_service.list_notes()
    config = current_app.config.get("CONFIG")
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template(
        "partials/notes_modal.html", notes=all_notes, config=public_config, config_json=serialized_public_config
    )


@main_bp.route("/partials/shopping-modal")
def shopping_modal():
    """Return the shopping modal partial."""
    from hub.services import shopping as shopping_service

    all_items = shopping_service.list_shopping_items()
    active_count = sum(1 for item in all_items if not item.done)
    config = current_app.config.get("CONFIG")
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template(
        "partials/shopping_modal.html",
        items=all_items,
        active_count=active_count,
        config=public_config,
        config_json=serialized_public_config,
    )


@main_bp.route("/partials/timers-modal")
def timers_modal():
    """Return the timers modal partial."""
    from hub.services import timers as timers_service

    active_timers = timers_service.list_active_timers()
    config = current_app.config.get("CONFIG")
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template(
        "partials/timers_modal.html", timers=active_timers, config=public_config, config_json=serialized_public_config
    )


@main_bp.route("/partials/kitchen-reference-modal")
def kitchen_reference_modal():
    """Return the kitchen reference modal partial."""
    config = current_app.config.get("CONFIG")
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template(
        "partials/kitchen_reference_modal.html", config=public_config, config_json=serialized_public_config
    )


@main_bp.route("/partials/folder-modal")
def folder_modal():
    """Return the folder modal partial."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("partials/folder_modal.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/health")
def health():
    """Health check endpoint."""
    from hub import __version__

    return {
        "status": "ok",
        "time": datetime.now().isoformat(),
        "versions": {"app": __version__},
        "platform": platform.version(),
        "python_version": platform.python_version(),
    }


@main_bp.route("/admin")
def admin():
    """Admin panel main view."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("admin/admin.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/admin/login")
def admin_login_page():
    """Admin login page."""
    return render_template("admin/login.html")


@main_bp.route("/admin/config")
def admin_config():
    """Admin configuration page."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("admin/config.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/admin/backup")
def admin_backup():
    """Admin backup page."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("admin/backup.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/admin/diagnostics")
def admin_diagnostics():
    """Admin diagnostics page."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("admin/diagnostics.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/admin/system")
def admin_system():
    """Admin system info page."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("admin/system.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/admin/updates")
def admin_updates():
    """Admin updates page."""
    config = current_app.config.get("CONFIG", {})
    public_config = build_public_config(config)
    serialized_public_config = get_serialized_public_config(config)
    return render_template("admin/updates.html", config=public_config, config_json=serialized_public_config)


@main_bp.route("/admin/performance-metrics")
def performance_metrics():
    """Performance metrics endpoint to report Chrome tab memory, photo cache size, and ticker payload size."""
    import os
    from datetime import datetime

    import psutil

    from hub.services.sports_ticker_service import _read_cache_file

    # Get system memory usage (simulating Chrome tab memory for the whole process)
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
    except Exception:
        memory_mb = 0
        current_app.logger.exception("Error getting memory usage")

    # Get photo cache size (approximate from the photo count and file sizes)
    try:
        # Use the lazy import approach for photo service
        from hub import services

        photo_service = services.photo_service
        photo_count = len(photo_service.get_photos(limit=10000))  # Get all photos to count
    except Exception:
        photo_count = 0
        current_app.logger.exception("Error getting photo cache size")

    # Get sports ticker payload size from cache
    try:
        ticker_data = _read_cache_file()
        ticker_size = 0
        ticker_game_count = 0
        if ticker_data:
            import json

            ticker_size = len(json.dumps(ticker_data))
            ticker_game_count = len(ticker_data.get("games", []))
    except Exception:
        ticker_size = 0
        ticker_game_count = 0
        current_app.logger.exception("Error getting ticker data")

    # Get timestamp
    timestamp = datetime.now().isoformat()

    metrics = {
        "timestamp": timestamp,
        "memory_mb": round(memory_mb, 2),
        "photo_count": photo_count,
        "ticker_payload_size_bytes": ticker_size,
        "ticker_game_count": ticker_game_count,
        "process_id": os.getpid(),
    }

    return jsonify(metrics)
