import os
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class CalendarConfig(BaseModel):
    kind: str
    ics_url: Optional[str] = None
    google: Optional[Dict[str, Any]] = None


class WeatherLocation(BaseModel):
    lat: float = 0.0  # Required but with default for backward compatibility
    lon: float = 0.0  # Required but with default for backward compatibility
    name: Optional[str] = None  # For city name, zip code, or address


class WeatherProvider(BaseModel):
    kind: str
    location: WeatherLocation


class SportsProvider(BaseModel):
    kind: str  # thesportsdb or espn
    api_key: Optional[str] = None  # for TheSportsDB
    favorite_teams: List[str] = Field(default_factory=list)  # list of team IDs or names to filter
    enabled_leagues: List[str] = Field(
        default_factory=lambda: ["nba", "nfl", "mlb", "nhl"]
    )  # leagues to fetch data for
    polling_cadence_defaults: Dict[str, int] = Field(
        default_factory=lambda: {"idle": 300, "active": 90, "post_final": 150}
    )  # seconds
    timeout_thresholds: Dict[str, int] = Field(default_factory=lambda: {"connect": 10, "read": 30})  # seconds
    scoreboard_endpoints: Dict[str, str] = Field(
        default_factory=lambda: {
            "nba": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
            "nfl": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
            "mlb": "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
            "nhl": "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
        }
    )  # Public ESPN scoreboard endpoints (no API keys required)


class WebhookConfig(BaseModel):
    url: str
    event_types: List[str] = Field(default_factory=lambda: ["weather_alert"])  # List of events to trigger this webhook
    active: bool = True
    name: str  # Name for identification
    secret: Optional[str] = None  # Optional secret for signing payloads
    headers: Optional[Dict[str, str]] = Field(default_factory=dict)  # Additional headers to send with request


class AppConfig(BaseModel):
    id: str
    label: str
    icon: str
    action: str
    target: Optional[str] = None
    url: Optional[str] = None


class SecurityConfig(BaseModel):
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    rate_limit_enabled: bool = True
    rate_limit_storage_uri: Optional[str] = None
    default_rate_limit: str = "60 per minute"
    admin_rate_limit: str = "10 per minute"
    ip_whitelist_enabled: bool = False
    ip_whitelist: List[str] = Field(default_factory=list)
    session_timeout: int = 3600  # 1 hour in seconds
    secure_headers: bool = True
    admin_username: Optional[str] = None
    admin_password_hash: Optional[str] = None  # Store hashed password
    admin_enabled: bool = False  # Whether admin panel is enabled
    socketio_allowed_origins: List[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5000", "http://localhost:5000"]
    )


class FeaturesConfig(BaseModel):
    voice: bool = False
    voice_wake_word: Optional[str] = "kitchen"
    kiosk: bool = True
    auth: bool = False
    plugins: bool = False  # Dormant unless deliberately enabled
    sports_ticker_clickable: bool = False  # Enable/disable click behavior for sports ticker items
    sports_ticker_enabled: bool = True  # Enable or disable the sports ticker display
    sports_ticker_mock_mode: bool = False  # Enable mock data for the sports ticker


class ServiceConfig(BaseModel):
    """Background service toggles that can be disabled on low-power deployments."""

    weather_alerts: bool = False  # Dormant unless deliberately enabled
    webhooks: bool = False  # Check configured webhook destinations
    update_checks: bool = False  # Check upstream releases from the appliance


class BurnInConfig(BaseModel):
    """Configuration for burn-in mitigation."""

    enabled: bool = False
    shift_enabled: bool = True
    dim_enabled: bool = True
    shift_interval_seconds: int = 180
    shift_range_px: int = 12
    dim_idle_seconds: int = 300
    dim_level: float = 0.6


class UIConfig(BaseModel):
    theme: str = "auto"  # light, dark, auto
    density: str = "comfortable"  # compact, comfortable
    burn_in: BurnInConfig = BurnInConfig()


class CommuteWindowConfig(BaseModel):
    """Time window for showing commute map."""

    start: str = "06:00"
    end: str = "09:00"


class CommuteConfig(BaseModel):
    """Configuration for commute map widget."""

    enabled: bool = True
    provider: str = "google"  # google or mapbox
    home_address: str = ""
    work_address: str = ""
    always_visible: bool = False
    morning_window: CommuteWindowConfig = CommuteWindowConfig(start="06:00", end="09:00")
    evening_window: CommuteWindowConfig = CommuteWindowConfig(start="16:30", end="18:30")
    google_api_key: Optional[str] = None
    mapbox_token: Optional[str] = None
    refresh_minutes: int = 2  # How often to refresh the route while visible
    model_config = ConfigDict(extra="allow")


class HomeAssistantConfig(BaseModel):
    base_url: str
    access_token: str


class PluginConfig(BaseModel):
    enabled: bool = False
    auto_update: bool = False
    allow_unsafe: bool = False  # Whether to allow potentially unsafe plugins
    max_plugins: int = 100  # Maximum number of plugins allowed
    plugin_directory: Optional[str] = None  # Custom plugin directory


class PluginSettings(BaseModel):
    """Configuration for individual plugins."""

    enabled: bool = True
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CastingDeviceConfig(BaseModel):
    """Configuration for a single casting device."""

    id: str
    name: str
    type: str  # google_cast, roku, alexa
    host: Optional[str] = None  # IP address or hostname
    port: Optional[int] = None


class CastingConfig(BaseModel):
    """Configuration for casting functionality."""

    enabled: bool = False
    discovery_enabled: bool = False
    discovery_interval: int = 300  # seconds
    default_volume: int = 50
    devices: List[CastingDeviceConfig] = Field(default_factory=list)
    auto_discover: bool = False


class PhotoConfig(BaseModel):
    """Configuration for photo functionality."""

    enabled: bool = False
    local_path: str = "./instance/photos"  # Path to local photos
    slideshow_interval: int = 5  # seconds between photos
    sync_enabled: bool = False  # Whether to sync from external sources
    google_photos: Optional[Dict[str, Any]] = None  # Google Photos config
    model_config = ConfigDict(extra="allow")


class ChoreConfig(BaseModel):
    """Configuration for chore functionality."""

    enabled: bool = False
    default_assignee: str = "family"  # Default assignee for new chores
    reminder_hours_before: int = 24  # Hours before due date to send reminder
    recurring_enabled: bool = True  # Whether to automatically create recurring chores
    default_priority: str = "normal"  # Default priority for new chores (low, normal, high, urgent)
    family_members: List[str] = Field(
        default_factory=lambda: ["parent", "child1", "child2"]
    )  # Available family members for assignment


class IoTConfig(BaseModel):
    """Configuration for IoT functionality."""

    enabled: bool = False
    discovery_enabled: bool = False
    discovery_interval: int = 300  # seconds between discovery attempts
    default_timeout: int = 10  # seconds for device communication timeout
    alexa_enabled: bool = True
    google_home_enabled: bool = True
    supported_device_types: List[str] = Field(default_factory=lambda: ["alexa", "google_home", "google_cast"])


class MusicConfig(BaseModel):
    """Configuration for music functionality."""

    enabled: bool = True
    local_path: str = "./instance/music"  # Path to local music files
    volume: int = 70  # Default volume (0-100)
    sync_enabled: bool = False  # Whether to sync from external services
    spotify: Optional[Dict[str, Any]] = None  # Spotify config
    apple_music: Optional[Dict[str, Any]] = None  # Apple Music config
    deezer: Optional[Dict[str, Any]] = None  # Deezer config
    model_config = ConfigDict(extra="allow")


class MediaConfig(BaseModel):
    """Configuration for media launcher functionality."""

    enabled: bool = True
    launcher_endpoint: str = "http://127.0.0.1:7666/v1/open_media"
    allowed_domains: List[str] = Field(
        default_factory=lambda: [
            "youtube.com",
            "youtu.be",
            "twitch.tv",
            "pluto.tv",
            "roku.com",
            "roku.tv",
            "vimeo.com",
            "dailymotion.com",
            "tubitv.com",
            "spotify.com",
            "disneyplus.com",
            "max.com",
            "espn.com",
            "photos.google.com",
            "google.com",
            "therokuchannel.roku.com",
        ]
    )


class CacheConfig(BaseModel):
    """Configuration for cache sizing and eviction."""

    max_entries: int = 1000
    max_size_mb: int = 50


class ConfigSchema(BaseModel):
    layout: Dict[str, Any]
    apps: List[AppConfig]
    extra_apps: List[AppConfig] = Field(default_factory=list)
    local_apps: List[AppConfig] = Field(default_factory=list)
    family: List[Dict[str, Any]] = Field(default_factory=list)
    providers: Dict[str, Any]  # This will contain calendar, weather, homeassistant, and sports configs
    features: FeaturesConfig
    services: ServiceConfig = ServiceConfig()
    ui: UIConfig
    security: SecurityConfig
    webhooks: Optional[List[WebhookConfig]] = Field(default_factory=list)  # List of configured webhooks
    plugins: Optional[Dict[str, PluginSettings]] = Field(default_factory=dict)  # Plugin-specific configurations
    plugin_config: PluginConfig = PluginConfig()  # Global plugin configuration
    casting: CastingConfig = CastingConfig()  # Casting configuration
    media: MediaConfig = MediaConfig()  # Media configuration
    photos: PhotoConfig = PhotoConfig()  # Photo configuration
    music: MusicConfig = MusicConfig()  # Music configuration
    chores: ChoreConfig = ChoreConfig()  # Chore configuration
    iot: IoTConfig = IoTConfig()  # IoT configuration
    commute: CommuteConfig = CommuteConfig()  # Commute map configuration
    cache: CacheConfig = CacheConfig()  # Cache sizing configuration
    external_api_limits: Dict[str, str] = Field(default_factory=dict)  # Rate limit overrides per service


def load_config(config_path: str) -> ConfigSchema:
    """
    Load and validate configuration from YAML file.

    Args:
        config_path: Path to the config file

    Returns:
        Validated configuration object

    Raises:
        ValueError: If config file is invalid
    """
    try:
        _load_env_file(_resolve_env_path(config_path))

        with open(config_path, encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}

        raw_config = _apply_env_overrides(raw_config)

        # Ensure security config exists, add default if missing
        if "security" not in raw_config:
            raw_config["security"] = SecurityConfig().model_dump()

        # Validate the configuration
        validated_config = ConfigSchema(**raw_config)

        return validated_config
    except ValidationError as e:
        error_msg = f"Configuration validation error: {e}"
        raise ValueError(error_msg) from e
    except FileNotFoundError as e:
        error_msg = f"Configuration file not found: {config_path}"
        raise ValueError(error_msg) from e
    except yaml.YAMLError as e:
        error_msg = f"YAML parsing error: {e}"
        raise ValueError(error_msg) from e


def _get_env(name: str) -> Optional[str]:
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _resolve_env_path(config_path: str) -> str:
    config_dir = os.path.dirname(os.path.abspath(config_path))
    return os.path.join(config_dir, ".env")


def _load_env_file(path: str) -> None:
    """Load simple KEY=VALUE pairs into os.environ if not already set."""
    if not os.path.exists(path):
        return

    try:
        with open(path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if not key or key in os.environ:
                    continue
                os.environ[key] = value
    except OSError:
        # If the env file can't be read, ignore and continue with existing environment.
        return


def _set_nested(config: Dict[str, Any], path: List[str], value: Optional[str]) -> None:
    if value is None:
        return
    cursor = config
    for key in path[:-1]:
        next_cursor = cursor.get(key)
        if not isinstance(next_cursor, dict):
            next_cursor = {}
            cursor[key] = next_cursor
        cursor = next_cursor
    cursor[path[-1]] = value


def _apply_env_overrides(raw_config: Dict[str, Any]) -> Dict[str, Any]:
    """Override sensitive config fields with environment variables when provided."""
    config = dict(raw_config)

    _set_nested(
        config, ["commute", "google_api_key"], _get_env("COMMUTE_GOOGLE_API_KEY") or _get_env("GOOGLE_MAPS_API_KEY")
    )
    _set_nested(config, ["commute", "mapbox_token"], _get_env("COMMUTE_MAPBOX_TOKEN") or _get_env("MAPBOX_TOKEN"))

    _set_nested(config, ["music", "spotify", "client_id"], _get_env("SPOTIFY_CLIENT_ID"))
    _set_nested(config, ["music", "spotify", "client_secret"], _get_env("SPOTIFY_CLIENT_SECRET"))
    _set_nested(config, ["music", "spotify", "redirect_uri"], _get_env("SPOTIFY_REDIRECT_URI"))

    _set_nested(
        config,
        ["providers", "calendar", "google", "client_id"],
        _get_env("GOOGLE_CALENDAR_CLIENT_ID") or _get_env("GOOGLE_CLIENT_ID"),
    )
    _set_nested(
        config,
        ["providers", "calendar", "google", "client_secret"],
        _get_env("GOOGLE_CALENDAR_CLIENT_SECRET") or _get_env("GOOGLE_CLIENT_SECRET"),
    )
    _set_nested(
        config, ["providers", "sports", "api_key"], _get_env("THESPORTSDB_API_KEY") or _get_env("SPORTS_API_KEY")
    )

    _set_nested(config, ["photos", "google_photos", "client_id"], _get_env("GOOGLE_PHOTOS_CLIENT_ID"))
    _set_nested(config, ["photos", "google_photos", "client_secret"], _get_env("GOOGLE_PHOTOS_CLIENT_SECRET"))
    _set_nested(config, ["photos", "google_photos", "refresh_token"], _get_env("GOOGLE_PHOTOS_REFRESH_TOKEN"))

    webhook_secret = _get_env("WEBHOOK_DEFAULT_SECRET")
    webhook_auth = _get_env("WEBHOOK_DEFAULT_AUTHORIZATION")
    if webhook_secret or webhook_auth:
        webhooks = config.get("webhooks")
        if isinstance(webhooks, list):
            for webhook in webhooks:
                if not isinstance(webhook, dict):
                    continue
                if webhook_secret and not webhook.get("secret"):
                    webhook["secret"] = webhook_secret
                if webhook_auth:
                    headers = webhook.get("headers")
                    if not isinstance(headers, dict):
                        headers = {}
                        webhook["headers"] = headers
                    headers.setdefault("Authorization", webhook_auth)

    return config
