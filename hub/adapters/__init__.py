"""Adapters package for Family Hub."""

from .alexa_adapter import AlexaAdapter, discover_alexa_devices
from .calendar_google import add_google_event, fetch_google_events
from .calendar_google import get_calendar_status as get_google_status
from .calendar_ics import fetch_ics_events
from .google_home_adapter import GoogleHomeAdapter, discover_google_home_devices
from .homeassistant import HomeAssistantAdapter, initialize_ha_adapter
from .news_aggregator import news_aggregator_adapter
from .sports_espn import ESPNAdapter
from .sports_thesportsdb import TheSportsDBAdapter
from .weather_openmeteo import get_current_weather, get_daily_forecast, get_hourly_forecast

# Handle optional imports that may not be available
try:
    from .google_cast_adapter import GoogleCastAdapter, discover_google_cast_devices
except ImportError as e:
    # Create placeholder functions if pychromecast is not available
    _google_cast_err = str(e)

    def GoogleCastAdapter(*args, **kwargs):
        raise ImportError(f"Google Cast adapter not available: {_google_cast_err}")

    def discover_google_cast_devices():
        return []


try:
    from .roku_adapter import RokuAdapter, discover_roku_devices
except ImportError as e:
    # Create placeholder functions if python-roku is not available
    _roku_err = str(e)

    def RokuAdapter(*args, **kwargs):
        raise ImportError(f"Roku adapter not available: {_roku_err}")

    def discover_roku_devices():
        return []
