import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

import requests

from hub.cache import get_cache, set_cache
from hub.geocode import parse_location_input
from hub.models import CurrentWeather, DailyForecast, HourlyForecast
from hub.utils.http import RateLimitError, rate_limited_get
from hub.utils.units import celsius_to_fahrenheit, kmh_to_mph

logger = logging.getLogger(__name__)


def _resolve_coordinates(lat: float, lon: float, location_name: str = None) -> Tuple[float, float]:
    """
    Resolve coordinates from either direct lat/lon or location name.

    Args:
        lat: Latitude if provided directly
        lon: Longitude if provided directly
        location_name: Location name, zip code, or address to geocode

    Returns:
        Tuple of (latitude, longitude)
    """
    if location_name:
        coords = parse_location_input(location_name)
        if coords:
            return coords
        else:
            # Fallback to provided coordinates if geocoding fails
            return (lat, lon)
    else:
        # Use direct coordinates
        return (lat, lon)


def mm_to_inches(mm: float) -> float:
    """Convert millimeters to inches."""
    return mm / 25.4


def get_current_weather(lat: float, lon: float, location_name: str = None) -> Dict[str, Any]:
    """
    Fetch current weather data from Open-Meteo API.

    Args:
        lat: Latitude of the location
        lon: Longitude of the location
        location_name: Optional location name, zip code, or address to geocode

    Returns:
        Dictionary with current weather data
    """
    # Resolve coordinates from either direct lat/lon or location name
    resolved_lat, resolved_lon = _resolve_coordinates(lat, lon, location_name)

    logger.debug(
        "Weather API using coordinates %s, %s for location '%s'",
        resolved_lat,
        resolved_lon,
        location_name,
    )

    # Create cache key for current weather
    # Version cache key so fixes to feels-like or other fields fetch fresh data
    cache_key = f"weather:v2:current:{resolved_lat}:{resolved_lon}"

    # Try to get from cache first
    cached_data = get_cache(cache_key)
    if cached_data:
        return cached_data

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": resolved_lat,
        "longitude": resolved_lon,
        "current_weather": "true",
        "temperature_unit": "celsius",
        "windspeed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "auto",
    }

    try:
        response = rate_limited_get(url, params=params, timeout=10, service_name="openmeteo")
        response.raise_for_status()

        data = response.json()

        current = data.get("current_weather", {})

        # Get additional data for severe weather detection
        # Adding hourly data to check for sudden weather changes
        hourly_data = _get_hourly_weather_details(resolved_lat, resolved_lon, 1)  # Get next hour's forecast

        # Convert temperature from Celsius to Fahrenheit
        temperature_c = current.get("temperature", 0)
        temperature_f = celsius_to_fahrenheit(temperature_c)

        # Convert wind speed from km/h to mph
        wind_speed_kmh = current.get("windspeed", 0)
        wind_speed_mph = kmh_to_mph(wind_speed_kmh)

        # Prefer provider-supplied apparent temperature; otherwise compute wind chill
        feels_like_value = current.get("apparent_temperature")
        if feels_like_value is not None:
            # Convert apparent temperature from Celsius to Fahrenheit
            feels_like_f = celsius_to_fahrenheit(feels_like_value)
        else:
            # Compute wind chill when it's cold and breezy; fallback to actual temp otherwise
            feels_like_f = temperature_f
            if temperature_f <= 50 and wind_speed_mph > 3:
                feels_like_f = (
                    35.74
                    + 0.6215 * temperature_f
                    - 35.75 * (wind_speed_mph**0.16)
                    + 0.4275 * temperature_f * (wind_speed_mph**0.16)
                )

        # Create and return current weather data
        current_weather = CurrentWeather(
            temperature=temperature_f,
            feels_like=feels_like_f,
            condition=_get_weather_description(current.get("weathercode", 0)),
            humidity=0,  # Open-Meteo doesn't provide humidity in current weather
            wind_speed=wind_speed_mph,
            location=location_name or f"{resolved_lat}, {resolved_lon}",  # Use location name if provided
        )

        result = current_weather.to_dict()

        # Add severe weather indicators to the result
        result["severe_weather_indicators"] = _analyze_severe_conditions(
            current, hourly_data[:1] if hourly_data else []
        )

        # Cache the result for 30 minutes
        set_cache(cache_key, result, ttl_seconds=1800)

        return result
    except RateLimitError as exc:
        logger.error("Open-Meteo current weather rate limited: %s", exc)
        return {}
    except requests.RequestException:
        logger.exception(
            "Open-Meteo current weather request failed for location '%s' (%s, %s)",
            location_name,
            resolved_lat,
            resolved_lon,
        )
        return {}
    except (KeyError, TypeError, ValueError):
        logger.exception(
            "Open-Meteo current weather parsing failed for location '%s' (%s, %s)",
            location_name,
            resolved_lat,
            resolved_lon,
        )
        return {}


def get_hourly_forecast(lat: float, lon: float, hours: int = 24, location_name: str = None) -> List[Dict[str, Any]]:
    """
    Fetch hourly weather forecast from Open-Meteo API.

    Args:
        lat: Latitude of the location
        lon: Longitude of the location
        hours: Number of hours to fetch (default 24)
        location_name: Optional location name, zip code, or address to geocode

    Returns:
        List of hourly forecast data
    """
    # Resolve coordinates from either direct lat/lon or location name
    resolved_lat, resolved_lon = _resolve_coordinates(lat, lon, location_name)

    # Create cache key for hourly forecast - v2 for added fields (apparent_temperature, precip, wind_gusts)
    cache_key = f"weather:hourly:v2:{resolved_lat}:{resolved_lon}:{hours}"

    # Try to get from cache first
    cached_data = get_cache(cache_key)
    if cached_data:
        return cached_data

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": resolved_lat,
        "longitude": resolved_lon,
        "hourly": [
            "temperature_2m",
            "apparent_temperature",
            "weathercode",
            "windspeed_10m",
            "wind_gusts_10m",
            "precipitation_probability",
            "precipitation",
            "rain",
            "showers",
            "snowfall",
        ],
        "temperature_unit": "celsius",
        "windspeed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "auto",
        "forecast_hours": hours,
    }

    try:
        response = rate_limited_get(url, params=params, timeout=10, service_name="openmeteo")
        response.raise_for_status()

        data = response.json()

        hourly_data = data.get("hourly", {})
        times = hourly_data.get("time", [])
        temperatures = hourly_data.get("temperature_2m", [])
        apparent_temperatures = hourly_data.get("apparent_temperature", [])
        weather_codes = hourly_data.get("weathercode", [])
        wind_speeds = hourly_data.get("windspeed_10m", [])
        wind_gusts = hourly_data.get("wind_gusts_10m", [])
        precip_probabilities = hourly_data.get("precipitation_probability", [])
        precipitation = hourly_data.get("precipitation", [])
        rain = hourly_data.get("rain", [])
        showers = hourly_data.get("showers", [])
        snowfall = hourly_data.get("snowfall", [])

        hourly_forecasts = []
        for i in range(
            min(
                len(times), len(temperatures), len(apparent_temperatures),
                len(weather_codes), len(wind_speeds), len(wind_gusts),
                len(precip_probabilities), len(precipitation),
                len(rain), len(showers), len(snowfall),
                hours,
            )
        ):
            time_str = times[i]
            time = (
                datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                if "Z" in time_str
                else datetime.fromisoformat(time_str)
            )

            # Convert temperature from Celsius to Fahrenheit
            temperature_c = temperatures[i]
            temperature_f = celsius_to_fahrenheit(temperature_c)

            # Convert apparent temperature from Celsius to Fahrenheit
            apparent_c = apparent_temperatures[i]
            apparent_f = celsius_to_fahrenheit(apparent_c)

            hourly_forecast = HourlyForecast(
                time=time, temperature=temperature_f, condition=_get_weather_description(weather_codes[i])
            )

            # Add additional fields for severe weather detection and forecast modal
            hourly_forecast_dict = hourly_forecast.to_dict()
            # Convert wind speed from km/h to mph
            hourly_forecast_dict["wind_speed"] = kmh_to_mph(wind_speeds[i]) if i < len(wind_speeds) else 0
            hourly_forecast_dict["wind_gust"] = kmh_to_mph(wind_gusts[i]) if i < len(wind_gusts) else 0
            hourly_forecast_dict["precipitation_probability"] = (
                precip_probabilities[i] if i < len(precip_probabilities) else 0
            )
            hourly_forecast_dict["feels_like"] = apparent_f
            hourly_forecast_dict["precipitation"] = precipitation[i] if i < len(precipitation) else 0
            hourly_forecast_dict["rain"] = rain[i] if i < len(rain) else 0
            hourly_forecast_dict["showers"] = showers[i] if i < len(showers) else 0
            hourly_forecast_dict["snowfall"] = snowfall[i] if i < len(snowfall) else 0
            hourly_forecast_dict["precipitation_in"] = mm_to_inches(hourly_forecast_dict["precipitation"])
            hourly_forecast_dict["rain_in"] = mm_to_inches(hourly_forecast_dict["rain"])
            hourly_forecast_dict["showers_in"] = mm_to_inches(hourly_forecast_dict["showers"])
            hourly_forecast_dict["snowfall_in"] = mm_to_inches(hourly_forecast_dict["snowfall"])

            hourly_forecasts.append(hourly_forecast_dict)

        # Cache the result for 30 minutes
        set_cache(cache_key, hourly_forecasts, ttl_seconds=1800)

        return hourly_forecasts
    except RateLimitError as exc:
        logger.error("Open-Meteo hourly forecast rate limited: %s", exc)
        return []
    except requests.RequestException:
        logger.exception(
            "Open-Meteo hourly forecast request failed for location '%s' (%s, %s)",
            location_name,
            resolved_lat,
            resolved_lon,
        )
        return []
    except (KeyError, TypeError, ValueError):
        logger.exception(
            "Open-Meteo hourly forecast parsing failed for location '%s' (%s, %s)",
            location_name,
            resolved_lat,
            resolved_lon,
        )
        return []


def _get_hourly_weather_details(
    lat: float, lon: float, hours: int = 24, location_name: str = None
) -> List[Dict[str, Any]]:
    """
    Internal function to get detailed hourly weather data including fields needed for severe weather detection.

    Args:
        lat: Latitude of the location
        lon: Longitude of the location
        hours: Number of hours to fetch
        location_name: Optional location name, zip code, or address to geocode

    Returns:
        List of hourly forecast data with additional fields
    """
    # Resolve coordinates from either direct lat/lon or location name
    resolved_lat, resolved_lon = _resolve_coordinates(lat, lon, location_name)

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": resolved_lat,
        "longitude": resolved_lon,
        "hourly": [
            "temperature_2m",
            "weathercode",
            "windspeed_10m",
            "precipitation_probability",
            "rain",
            "showers",
            "snowfall",
        ],
        "temperature_unit": "celsius",
        "windspeed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "auto",
        "forecast_hours": hours,
    }

    try:
        response = rate_limited_get(url, params=params, timeout=10, service_name="openmeteo")
        response.raise_for_status()

        data = response.json()

        hourly_data = data.get("hourly", {})
        times = hourly_data.get("time", [])
        temperatures = hourly_data.get("temperature_2m", [])
        weather_codes = hourly_data.get("weathercode", [])
        wind_speeds = hourly_data.get("windspeed_10m", [])
        precip_probabilities = hourly_data.get("precipitation_probability", [])
        rain = hourly_data.get("rain", [])
        showers = hourly_data.get("showers", [])
        snowfall = hourly_data.get("snowfall", [])

        hourly_details = []
        for i in range(
            min(
                len(times),
                len(temperatures),
                len(weather_codes),
                len(wind_speeds),
                len(precip_probabilities),
                len(rain),
                len(showers),
                len(snowfall),
                hours,
            )
        ):
            time_str = times[i]
            time = (
                datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                if "Z" in time_str
                else datetime.fromisoformat(time_str)
            )

            # Convert temperature from Celsius to Fahrenheit
            temperature_c = temperatures[i]
            temperature_f = celsius_to_fahrenheit(temperature_c)

            hourly_detail = {
                "time": time,
                "temperature": temperature_f,
                "condition": _get_weather_description(weather_codes[i]),
                "weather_code": weather_codes[i],
                "wind_speed": kmh_to_mph(wind_speeds[i]),  # Convert km/h to mph
                "precipitation_probability": precip_probabilities[i],
                "rain": rain[i],
                "showers": showers[i],
                "snowfall": snowfall[i],
            }

            hourly_details.append(hourly_detail)

        return hourly_details
    except RateLimitError as exc:
        logger.error("Open-Meteo hourly detail rate limited: %s", exc)
        return []
    except requests.RequestException:
        logger.exception(
            "Open-Meteo hourly detail request failed for location '%s' (%s, %s)",
            location_name,
            resolved_lat,
            resolved_lon,
        )
        return []
    except (KeyError, TypeError, ValueError):
        logger.exception(
            "Open-Meteo hourly detail parsing failed for location '%s' (%s, %s)",
            location_name,
            resolved_lat,
            resolved_lon,
        )
        return []


def get_daily_forecast(lat: float, lon: float, days: int = 7, location_name: str = None) -> List[Dict[str, Any]]:
    """
    Fetch daily weather forecast from Open-Meteo API.

    Args:
        lat: Latitude of the location
        lon: Longitude of the location
        days: Number of days to fetch (default 7)
        location_name: Optional location name, zip code, or address to geocode

    Returns:
        List of daily forecast data
    """
    # Resolve coordinates from either direct lat/lon or location name
    resolved_lat, resolved_lon = _resolve_coordinates(lat, lon, location_name)

    # Create cache key for daily forecast
    cache_key = f"weather:daily:{resolved_lat}:{resolved_lon}:{days}"

    # Try to get from cache first
    cached_data = get_cache(cache_key)
    if cached_data:
        return cached_data

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": resolved_lat,
        "longitude": resolved_lon,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "weathercode",
            "precipitation_probability_max",
            "windspeed_10m_max",
            "wind_gusts_10m_max",
        ],
        "temperature_unit": "celsius",
        "windspeed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "auto",
        "forecast_days": days,
    }

    try:
        response = rate_limited_get(url, params=params, timeout=10, service_name="openmeteo")
        response.raise_for_status()

        data = response.json()

        daily_data = data.get("daily", {})
        times = daily_data.get("time", [])
        max_temps = daily_data.get("temperature_2m_max", [])
        min_temps = daily_data.get("temperature_2m_min", [])
        weather_codes = daily_data.get("weathercode", [])
        precip_prob_max = daily_data.get("precipitation_probability_max", [])
        wind_speed_max = daily_data.get("windspeed_10m_max", [])
        wind_gust_max = daily_data.get("wind_gusts_10m_max", [])

        daily_forecasts = []
        for i in range(
            min(
                len(times),
                len(max_temps),
                len(min_temps),
                len(weather_codes),
                len(precip_prob_max),
                len(wind_speed_max),
                len(wind_gust_max),
                days,
            )
        ):
            time_str = times[i]
            date = (
                datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                if "Z" in time_str
                else datetime.fromisoformat(time_str)
            )

            # Convert temperatures from Celsius to Fahrenheit
            high_temp_c = max_temps[i]
            high_temp_f = celsius_to_fahrenheit(high_temp_c)
            low_temp_c = min_temps[i]
            low_temp_f = celsius_to_fahrenheit(low_temp_c)

            daily_forecast = DailyForecast(
                date=date, high=high_temp_f, low=low_temp_f, condition=_get_weather_description(weather_codes[i])
            )

            # Add additional fields for severe weather detection and forecast modal
            daily_forecast_dict = daily_forecast.to_dict()
            # Convert max wind speed from km/h to mph
            daily_forecast_dict["max_wind_speed"] = kmh_to_mph(wind_speed_max[i]) if i < len(wind_speed_max) else 0
            daily_forecast_dict["max_wind_gust"] = kmh_to_mph(wind_gust_max[i]) if i < len(wind_gust_max) else 0
            daily_forecast_dict["max_precip_probability"] = precip_prob_max[i] if i < len(precip_prob_max) else 0

            daily_forecasts.append(daily_forecast_dict)

        # Cache the result for 1 hour
        set_cache(cache_key, daily_forecasts, ttl_seconds=3600)

        return daily_forecasts
    except RateLimitError as exc:
        logger.error("Open-Meteo daily forecast rate limited: %s", exc)
        return []
    except requests.RequestException:
        logger.exception(
            "Open-Meteo daily forecast request failed for location '%s' (%s, %s)",
            location_name,
            resolved_lat,
            resolved_lon,
        )
        return []
    except (KeyError, TypeError, ValueError):
        logger.exception(
            "Open-Meteo daily forecast parsing failed for location '%s' (%s, %s)",
            location_name,
            resolved_lat,
            resolved_lon,
        )
        return []


def _analyze_severe_conditions(current_data: Dict, hourly_data: List[Dict]) -> List[str]:
    """
    Analyze current and forecast weather data to identify potential severe conditions.

    Args:
        current_data: Current weather data from Open-Meteo
        hourly_data: Upcoming hourly forecast data

    Returns:
        List of severe weather condition types detected
    """
    severe_conditions = []

    # Check current conditions
    temp = current_data.get("temperature", 0)
    wind_speed = current_data.get("windspeed", 0)
    weather_code = current_data.get("weathercode", 0)

    # Check for extreme temperatures
    if temp > 35:
        severe_conditions.append("high_temperature")
    elif temp < 0:
        severe_conditions.append("freezing_temperature")

    # Check for high wind speeds (threshold > 50 km/h)
    if wind_speed > 50:
        severe_conditions.append("high_wind")

    # Check for severe weather codes (from WMO codes)
    if weather_code in [95, 96, 99]:  # Thunderstorms (with hail)
        severe_conditions.append("thunderstorm")
    elif weather_code in [65, 82]:  # Heavy rain, violent rain showers
        severe_conditions.append("heavy_rain")
    elif weather_code in [75, 86]:  # Heavy snow, heavy snow showers
        severe_conditions.append("heavy_snow")

    # Check hourly forecast for additional conditions
    for hour in hourly_data:
        if isinstance(hour, dict):
            hour_wind = hour.get("wind_speed", 0)
            hour_precip = hour.get("precipitation_probability", 0)

            if hour_wind > 60:
                if "high_wind" not in severe_conditions:
                    severe_conditions.append("high_wind")
            if hour_precip > 80:
                if "heavy_precipitation" not in severe_conditions:
                    severe_conditions.append("heavy_precipitation")

    return severe_conditions


def _get_weather_description(code: int) -> str:
    """
    Convert weather code to description.
    Weather codes from WMO (World Meteorological Organization)
    """
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

    return weather_descriptions.get(code, "Unknown")