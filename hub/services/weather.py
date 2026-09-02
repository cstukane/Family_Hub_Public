from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Optional

from flask import current_app

from hub.adapters.weather_openmeteo import get_current_weather, get_daily_forecast, get_hourly_forecast
from hub.cache import get_cache
from hub.utils.config_helpers import get_config_value

_SNAPSHOT_LOCK = Lock()
_SNAPSHOT: Dict[str, Any] = {"data": None, "fetched_at": None}


@dataclass
class CurrentWeather:
    temperature: float
    feels_like: Optional[float]
    condition: str
    humidity: Optional[int]
    wind_speed: Optional[float]
    location: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "feels_like": self.feels_like,
            "condition": self.condition,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "location": self.location,
        }


@dataclass
class HourlyForecast:
    time: datetime
    temperature: float
    condition: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": self.time.isoformat() if self.time else None,
            "temperature": self.temperature,
            "condition": self.condition,
        }


@dataclass
class DailyForecast:
    date: datetime
    high: float
    low: float
    condition: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat() if self.date else None,
            "high": self.high,
            "low": self.low,
            "condition": self.condition,
        }


def get_weather_data(force_refresh: bool = False, max_age_seconds: int = 900) -> Dict[str, Any]:
    """
    Get all weather data (current, hourly, daily) from the configured provider.

    Returns:
        Dictionary containing current, hourly, and daily weather data
    """
    try:
        if not force_refresh:
            with _SNAPSHOT_LOCK:
                snapshot_data = _SNAPSHOT.get("data")
                snapshot_time = _SNAPSHOT.get("fetched_at")
            if snapshot_data and isinstance(snapshot_time, datetime):
                snapshot_age = (datetime.now(timezone.utc) - snapshot_time).total_seconds()
                if snapshot_age <= max_age_seconds:
                    return deepcopy(snapshot_data)

        config = current_app.config.get("CONFIG")
        if not config:
            current_app.logger.error("CONFIG not found in app config")
            return {"error": "Weather configuration missing"}

        providers = get_config_value(config, ("providers",))
        if not providers:
            current_app.logger.error("CONFIG has no 'providers' attribute or key")
            return {"error": "Weather providers configuration missing"}

        weather_config = get_config_value(config, ("providers", "weather"))
        if not weather_config:
            current_app.logger.error("Providers has no 'weather' attribute or key")
            current_app.logger.error(f"Providers type: {type(providers)}, content: {providers}")
            return {"error": "Weather provider configuration missing"}

        weather_location = get_config_value(config, ("providers", "weather", "location"))
        if not weather_location:
            current_app.logger.error("Weather config has no 'location' attribute or key")
            return {"error": "Weather location configuration missing"}

        # Determine the location to use - check format depending on how location was loaded
        if hasattr(weather_location, "name"):
            location_name = weather_location.name
            lat = weather_location.lat
            lon = weather_location.lon
        elif isinstance(weather_location, dict):
            location_name = weather_location.get("name")
            lat = weather_location.get("lat", 0.0)
            lon = weather_location.get("lon", 0.0)
        else:
            # Default fallback
            location_name = getattr(weather_location, "name", None)
            lat = getattr(weather_location, "lat", 0.0)
            lon = getattr(weather_location, "lon", 0.0)

        current_app.logger.info(
            f"Getting weather data for location: {location_name}, fallback coordinates: ({lat}, {lon})"
        )

        # Get current weather
        current = get_current_weather(lat, lon, location_name)
        if not current:
            current_app.logger.error("Failed to fetch current weather data")
            return {"error": "Weather provider unavailable"}
        current_app.logger.info(
            "Current weather: %s F, %s in %s",
            current.get("temperature", "N/A"),
            current.get("condition", "N/A"),
            current.get("location", "N/A"),
        )

        # Get hourly forecast
        hourly = get_hourly_forecast(lat, lon, 24, location_name)
        if not hourly:
            current_app.logger.warning("Hourly forecast unavailable for location: %s", location_name)
        current_app.logger.info(
            "Hourly forecast: %s hours, first temp: %s F",
            len(hourly),
            hourly[0].get("temperature", "N/A") if hourly else "N/A",
        )

        # Get daily forecast
        daily = get_daily_forecast(lat, lon, 7, location_name)
        if not daily:
            current_app.logger.warning("Daily forecast unavailable for location: %s", location_name)
        current_app.logger.info(
            "Daily forecast: %s days, first temp: H:%s F L:%s F",
            len(daily),
            daily[0].get("high", "N/A") if daily else "N/A",
            daily[0].get("low", "N/A") if daily else "N/A",
        )

        # Check cache timestamps - we need to use resolved coordinates for cache keys
        from hub.adapters.weather_openmeteo import _resolve_coordinates

        resolved_lat, resolved_lon = _resolve_coordinates(lat, lon, location_name)

        cache_keys = [
            f"weather:v2:current:{resolved_lat}:{resolved_lon}",
            f"weather:hourly:v2:{resolved_lat}:{resolved_lon}:24",
            f"weather:daily:{resolved_lat}:{resolved_lon}:7",
        ]

        for key in cache_keys:
            # Get the cache entry to check the update time
            cache_entry = get_cache(key)
            if cache_entry is not None:
                # The cache entry exists, so we need to check when it was updated
                # This is handled by the cache implementation itself
                pass

        snapshot = {
            "current": current,
            "hourly": hourly,
            "daily": daily,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        with _SNAPSHOT_LOCK:
            _SNAPSHOT["data"] = deepcopy(snapshot)
            _SNAPSHOT["fetched_at"] = datetime.now(timezone.utc)
        return snapshot
    except Exception:
        current_app.logger.exception("Error getting weather data")
        return {"error": "Weather data retrieval failed"}
