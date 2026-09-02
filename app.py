import contextlib
import os
import re
import secrets
import threading
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from flask_talisman import Talisman

from hub.utils.runtime import get_runtime_root


def _ensure_datetime(value):
    """Convert supported value types into a datetime, if possible."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        normalized = cleaned.replace("Z", "+00:00")
        # Try ISO 8601 first, then HH:MM fallback
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            with contextlib.suppress(ValueError):
                return datetime.strptime(normalized, "%H:%M")
            with contextlib.suppress(ValueError):
                return datetime.strptime(normalized, "%I:%M %p")
    return None


def format_time_12hour(dt):
    """Convert value to 12-hour format with lowercase a.m./p.m."""
    parsed = _ensure_datetime(dt)
    if parsed is None:
        return ""

    hour = parsed.hour
    minute = parsed.minute
    if hour == 0:
        return f"12:{minute:02d} a.m."
    if hour == 12:
        return f"12:{minute:02d} p.m."
    if hour < 12:
        return f"{hour}:{minute:02d} a.m."
    hour_12 = hour - 12
    return f"{hour_12}:{minute:02d} p.m."


def format_datetime_12hour(dt):
    """Convert datetime to MM/DD 12-hour format with lowercase a.m./p.m."""
    parsed = _ensure_datetime(dt)
    if parsed is None:
        return ""

    date_part = parsed.strftime("%m/%d")
    time_part = format_time_12hour(parsed)
    return f"{date_part} {time_part}".strip()


def format_time_12hour_compact(dt):
    """Convert value to a compact 12-hour format without minutes when on the hour."""
    parsed = _ensure_datetime(dt)
    if parsed is None:
        return ""

    hour = parsed.hour % 12 or 12
    suffix = "AM" if parsed.hour < 12 else "PM"
    minute = parsed.minute
    if minute:
        return f"{hour}:{minute:02d} {suffix}"
    return f"{hour} {suffix}"


def format_date_m_d(value):
    """Convert value to M/D format without leading zeros."""
    parsed = _ensure_datetime(value)
    if parsed is None:
        return ""

    return f"{parsed.month}/{parsed.day}"


def format_day_of_week(value):
    """Convert value to a 3-letter day-of-week abbreviation (e.g. 'Sat')."""
    parsed = _ensure_datetime(value)
    if parsed is None:
        return ""

    return parsed.strftime("%a")


def celsius_to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit."""
    return round((celsius * 9 / 5) + 32, 1)


def kmh_to_mph(kmh):
    """Convert km/h to mph."""
    return round(kmh * 0.621371, 1)


def weather_code_to_description(code):
    """Convert weather code to human-readable description."""
    weather_descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return weather_descriptions.get(int(code), "Unknown")


def convert_to_timezone(dt, tz_name="UTC"):
    """Convert datetime to specified timezone."""
    parsed = _ensure_datetime(dt)
    if parsed is None:
        return None

    # If the datetime is naive (no timezone), assume it's UTC
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))

    # Convert to the target timezone
    target_tz = ZoneInfo(tz_name)
    converted_dt = parsed.astimezone(target_tz)

    return converted_dt


def _normalize_event_title_for_display(title):
    """Normalize event titles for display-level deduplication."""
    return re.sub(r"\s+", " ", (title or "").strip()).casefold()


def group_events_by_date_for_template(events, target_date):
    """Filter and sort events for a specific date for the calendar template."""
    from datetime import datetime

    # Use the convert_to_timezone function from this module
    day_events = [
        event for event in events if event.starts_at and convert_to_timezone(event.starts_at).date() == target_date
    ]
    # Sort events by start time within the day (converted to local timezone)
    day_events.sort(key=lambda e: convert_to_timezone(e.starts_at) if e.starts_at else datetime.max)
    deduped_events = []
    seen = set()
    for event in day_events:
        start_local = convert_to_timezone(event.starts_at) if event.starts_at else None
        end_local = convert_to_timezone(event.ends_at) if event.ends_at else start_local
        key = (
            bool(getattr(event, "all_day", False)),
            _normalize_event_title_for_display(getattr(event, "title", "")),
            start_local.isoformat() if start_local else None,
            end_local.isoformat() if end_local else None,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped_events.append(event)
    return deduped_events


from hub import routes  # noqa: E402
from hub.config import load_config  # noqa: E402
from hub.db import init_app, init_db_command  # noqa: E402
from hub.plugins.manager import plugin_manager  # noqa: E402
from hub.scheduler import create_scheduler  # noqa: E402
from hub.sockets import init_socket_handlers, start_timer_monitor  # noqa: E402
from hub.utils.logging_config import configure_logging  # noqa: E402

# Initialize SocketIO without attaching to app initially
socketio = SocketIO()

# Initialize Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60 per minute"],  # Default limit
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)

# Security headers configuration
SECURITY_HEADERS = {
    "strict_transport_security": {
        "max_age": 31556952,  # 1 year in seconds
        "include_subdomains": True,
    },
    "frame_options": "SAMEORIGIN",
    "content_security_policy": {
        "default-src": "'self'",
        "script-src": [
            "'self'",
            "'unsafe-inline'",
            "https://unpkg.com",
            "https://cdnjs.cloudflare.com",
            "https://cdn.jsdelivr.net",
            "https://api.mapbox.com",
        ],
        "style-src": [
            "'self'",
            "'unsafe-inline'",
            "https://cdn.jsdelivr.net",
            "https://api.mapbox.com",
            "https://fonts.googleapis.com",
        ],
        "img-src": ["'self'", "data:", "https:", "https://api.mapbox.com"],
        "connect-src": [
            "'self'",
            "https://*.open-meteo.com",
            "https://www.thesportsdb.com",
            "wss:",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
            "https://api.mapbox.com",
            "https://events.mapbox.com",
        ],
        "frame-src": [
            "'self'",
            "https://www.youtube.com",
            "https://www.youtube-nocookie.com",
            "https://pluto.tv",
            "https://open.spotify.com",
        ],
        "font-src": ["'self'", "https:"],
        "object-src": "'none'",
        "media-src": ["'self'", "https:"],
    },
    "referrer_policy": "strict-origin-when-cross-origin",
}


def _is_service_enabled(config, field, default=False):
    """Helper to read background service toggles safely."""
    services_cfg = getattr(config, "services", None)
    if services_cfg is None:
        return default
    return getattr(services_cfg, field, default)


def _start_casting_discovery(app: Flask, config):
    """Launch casting discovery in a background thread when enabled."""
    casting_cfg = getattr(config, "casting", None)
    if not casting_cfg or not getattr(casting_cfg, "enabled", False):
        return
    if not getattr(casting_cfg, "discovery_enabled", True):
        return

    from hub.services import casting_manager

    def start_discovery():
        with app.app_context():
            casting_manager.refresh_device_list()

    threading.Thread(target=start_discovery, daemon=True).start()


def _prime_dashboard_caches(app: Flask) -> None:
    """Warm core dashboard caches (weather, calendar, sports ticker) as soon as the app boots."""

    def _worker():
        with app.app_context():
            now = datetime.now()
            horizon = now + timedelta(days=30)

            try:
                from hub.services import weather

                weather.get_weather_data()
            except Exception as exc:  # pragma: no cover - best effort warmup
                app.logger.warning("Weather cache prime failed: %s", exc)

            try:
                from hub.services import calendar

                calendar.list_events(now, horizon)
            except Exception as exc:  # pragma: no cover
                app.logger.warning("Calendar cache prime failed: %s", exc)

            try:
                config = app.config.get("CONFIG")
                features_cfg = getattr(config, "features", None) if config else None
                sports_ticker_enabled = True
                if features_cfg is not None:
                    sports_ticker_enabled = getattr(features_cfg, "sports_ticker_enabled", True)
                if sports_ticker_enabled:
                    from hub.services import sports_ticker_service

                    sports_ticker_service.get_sports_ticker_data()
            except Exception as exc:  # pragma: no cover
                app.logger.warning("Sports ticker cache prime failed: %s", exc)

    threading.Thread(target=_worker, daemon=True).start()


def _default_config_path() -> str:
    """Use the untracked deployment config, falling back to the safe example."""
    config_env = os.environ.get("FAMILY_HUB_CONFIG")
    if config_env:
        return config_env

    runtime_root = get_runtime_root()
    candidate = os.path.join(runtime_root, "config.yaml")
    if os.path.exists(candidate):
        return candidate
    return "config.example.yaml"


def create_app(config_path: str | None = None) -> Flask:
    """Application factory to create and configure the Flask app."""

    app = Flask(__name__, instance_relative_config=True)
    if os.environ.get("PYTEST_CURRENT_TEST"):
        app.config["TESTING"] = True

    _instance_path_override = os.environ.get("FAMILY_HUB_INSTANCE_PATH")
    if _instance_path_override:
        app.instance_path = os.path.abspath(_instance_path_override)

    configure_logging(app)

    # Load configuration. Real deployments keep their YAML in the ignored instance directory.
    config_path = config_path or _default_config_path()
    config = load_config(config_path)
    app.config["CONFIG"] = config
    app.config["CONFIG_PATH"] = config_path
    app.config["DATABASE"] = os.path.join(app.instance_path, "family_hub.db")

    # Configure secret key for sessions
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        secret_key = secrets.token_urlsafe(48)
        os.environ["SECRET_KEY"] = secret_key
        app.logger.warning("SECRET_KEY is not set; generated a temporary key for this session.")
    app.secret_key = secret_key

    # Configure secure session settings
    session_cookie_secure = bool(config.security.ssl_enabled or app.config.get("TESTING"))
    app.config.update(
        SESSION_COOKIE_SECURE=session_cookie_secure,  # Only send cookies over HTTPS when SSL is enabled
        SESSION_COOKIE_HTTPONLY=True,  # Prevent XSS by not allowing JS access to session cookie
        SESSION_COOKIE_SAMESITE="Lax",  # CSRF protection
        PERMANENT_SESSION_LIFETIME=config.security.session_timeout,  # Session timeout from config
    )

    # Set up the session configuration
    app.permanent_session_lifetime = timedelta(seconds=config.security.session_timeout)

    # Create instance folder if it doesn't exist
    with contextlib.suppress(OSError):
        os.makedirs(app.instance_path)

    # Initialize rate limiter with app configuration
    if config.security.rate_limit_enabled:
        storage_uri = config.security.rate_limit_storage_uri or os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
        app.config["RATELIMIT_STORAGE_URI"] = storage_uri
        limiter._storage_uri = storage_uri  # type: ignore[attr-defined]
        if config.security.default_rate_limit:
            limiter._default_limits = [config.security.default_rate_limit]  # type: ignore[attr-defined]
        limiter.init_app(app)

    # Initialize Talisman for security headers if enabled
    if config.security.secure_headers:
        talisman_kwargs = deepcopy(SECURITY_HEADERS)
        if not config.security.ssl_enabled:
            talisman_kwargs.pop("strict_transport_security", None)
        Talisman(app, force_https=config.security.ssl_enabled, **talisman_kwargs)

    # Initialize database
    init_app(app)
    with app.app_context():
        from hub.db import init_db

        init_db()

    # Initialize admin account if needed
    from hub.db import init_admin_account

    init_admin_account(app)

    # Note: Weather cache is now cleared by the scheduler job rather than on startup
    # to avoid issues with application context during initialization

    # Initialize and start scheduler
    app.scheduler = create_scheduler(app)

    # Initialize SocketIO with the app
    allowed_origins = []
    env_origins = os.environ.get("SOCKETIO_ALLOWED_ORIGINS")
    if env_origins:
        allowed_origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
    elif getattr(config.security, "socketio_allowed_origins", None):
        allowed_origins = list(config.security.socketio_allowed_origins)
    else:
        allowed_origins = ["http://127.0.0.1:5000", "http://localhost:5000"]
    socketio.init_app(
        app,
        cors_allowed_origins=allowed_origins,
        ping_interval=25,
        ping_timeout=60,
    )

    # Initialize socket event handlers
    init_socket_handlers(socketio)

    # Start the timer monitoring thread with app context
    start_timer_monitor(socketio, app)

    # Register blueprints from routes module
    app.register_blueprint(routes.main_bp)
    app.register_blueprint(routes.api_bp)

    # Register CLI commands
    app.cli.add_command(init_db_command)

    # The plugin system is attic code: do not initialize or scan disk unless opted in.
    if config.features.plugins and config.plugin_config.enabled:
        plugin_manager.init_app(app)
        installed_plugins = plugin_manager.get_installed_plugins()
        for plugin_name in installed_plugins:
            # Load the plugin
            load_result = plugin_manager.load_plugin(plugin_name)
            if load_result.success:
                # Initialize the plugin
                initialized = plugin_manager.initialize_plugin(plugin_name)
                if initialized:
                    # Enable the plugin if it's configured to be enabled
                    plugin_config = getattr(config, "plugins", {})
                    plugin_settings = plugin_config.get(plugin_name, {})
                    auto_enable = plugin_settings.get("enabled", True)
                    if auto_enable:
                        plugin_manager.enable_plugin(plugin_name)

    # Initialize casting device manager if casting is enabled
    _start_casting_discovery(app, config)

    # Initialize and start photo and music services if enabled in config
    if config.photos.enabled:
        from hub.services import photo_service

        # Sync photos if enabled
        if config.photos.sync_enabled:

            def sync_photos():
                with app.app_context():
                    photo_service.sync_photos_from_sources()

            sync_thread = threading.Thread(target=sync_photos, daemon=True)
            sync_thread.start()

    if config.music.enabled:
        from hub.services import music_service

        # Sync music if enabled
        if config.music.sync_enabled:

            def sync_music():
                with app.app_context():
                    music_service.sync_tracks_from_sources()

            sync_thread = threading.Thread(target=sync_music, daemon=True)
            sync_thread.start()

    # Prime weather/calendar/sports caches so UI has data immediately on load
    if not app.config.get("TESTING"):
        _prime_dashboard_caches(app)

    # Register custom Jinja filters
    app.jinja_env.filters["time_12hour"] = format_time_12hour
    app.jinja_env.filters["datetime_12hour"] = format_datetime_12hour
    app.jinja_env.filters["time_12hour_compact"] = format_time_12hour_compact
    app.jinja_env.filters["date_m_d"] = format_date_m_d
    app.jinja_env.filters["day_of_week"] = format_day_of_week
    app.jinja_env.filters["celsius_to_fahrenheit"] = celsius_to_fahrenheit
    app.jinja_env.filters["kmh_to_mph"] = kmh_to_mph
    app.jinja_env.filters["weather_code_to_description"] = weather_code_to_description
    app.jinja_env.filters["convert_to_timezone"] = convert_to_timezone
    app.jinja_env.globals["group_events_by_date"] = group_events_by_date_for_template

    # Store socketio instance in app for use in other modules
    app.socketio = socketio

    return app
