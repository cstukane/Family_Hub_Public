"""Geocoding utilities for converting location names to coordinates."""

import logging
import time
from typing import Optional, Tuple

from hub.utils.http import RateLimitError, rate_limited_get

_CACHE: dict = {}
_CACHE_TTL_SECONDS = 6 * 60 * 60
_FAIL_TTL_SECONDS = 5 * 60
_RATE_LIMIT_COOLDOWN_SECONDS = 60
_COOLDOWN_UNTIL = 0.0
_LAST_RATE_LIMIT_LOG = 0.0
_logger = logging.getLogger(__name__)


def geocode_location(location_str: str) -> Optional[Tuple[float, float]]:
    """
    Geocode a location string (city name, zip code, address) to latitude and longitude.

    Args:
        location_str: Location string (e.g., "New York, NY", "10001", "London")

    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    global _COOLDOWN_UNTIL, _LAST_RATE_LIMIT_LOG
    # Using OpenCage Geocoding API (free tier available)
    # Alternative: Nominatim (OpenStreetMap) which is completely free but has rate limits

    # For this implementation, we'll use Nominatim which is free
    # But with a fallback to fixed coordinates if API fails
    now = time.time()
    cached = _CACHE.get(location_str)
    if cached and cached.get("expires", 0) > now:
        return cached.get("coords")
    if now < _COOLDOWN_UNTIL:
        return None

    try:
        # Check if it looks like a US zip code (5 digits)
        # If so, append "United States" to improve geocoding accuracy
        import re

        if re.match(r"^\d{5}$", location_str.strip()):
            # This looks like a US zip code, append "United States" for better results
            search_query = f"{location_str} United States"
        else:
            search_query = location_str

        # URL encode the location string
        import urllib.parse

        encoded_location = urllib.parse.quote(search_query)

        # Use Nominatim (OpenStreetMap geocoding service)
        url = f"https://nominatim.openstreetmap.org/search?q={encoded_location}&format=json&limit=1"

        # Add a proper user agent as required by Nominatim
        headers = {"User-Agent": "KitchenHub/1.0 (https://github.com/your-project)"}

        response = rate_limited_get(url, headers=headers, timeout=10, service_name="nominatim")

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                coords = (lat, lon)
                _CACHE[location_str] = {"coords": coords, "expires": now + _CACHE_TTL_SECONDS}
                return coords
            else:
                _logger.info("Geocoding returned no results for: %s", location_str)
        else:
            _logger.warning(
                "Geocoding API returned status code %s for: %s",
                response.status_code,
                location_str,
            )

        # If API fails or doesn't return results, return None
        _CACHE[location_str] = {"coords": None, "expires": now + _FAIL_TTL_SECONDS}
        return None
    except RateLimitError as e:
        _COOLDOWN_UNTIL = time.time() + _RATE_LIMIT_COOLDOWN_SECONDS
        if time.time() - _LAST_RATE_LIMIT_LOG > _RATE_LIMIT_COOLDOWN_SECONDS:
            _logger.warning("Geocoding rate limited for '%s': %s", location_str, e)
            _LAST_RATE_LIMIT_LOG = time.time()
        _CACHE[location_str] = {"coords": None, "expires": time.time() + _FAIL_TTL_SECONDS}
        return None
    except Exception as e:
        # In case of any error, return None to use fallback coordinates
        _logger.warning("Geocoding failed for '%s': %s", location_str, e)
        _CACHE[location_str] = {"coords": None, "expires": now + _FAIL_TTL_SECONDS}
        return None


def parse_location_input(location_input: str) -> Optional[Tuple[float, float]]:
    """
    Parse location input which might be coordinates, zip code, or city name.

    Args:
        location_input: Input string that could be coordinates, zip, or city

    Returns:
        Tuple of (latitude, longitude) or None if unable to parse
    """
    # First check if it's already coordinates in the format "lat,lon"
    if "," in location_input:
        try:
            parts = location_input.split(",")
            if len(parts) == 2:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                # Validate coordinate ranges
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
        except ValueError:
            pass  # Not valid coordinates, continue to geocode

    # Check if it looks like a US zip code (5 digits)
    if location_input.strip().isdigit() and len(location_input.strip()) == 5:
        # Use the geocoding service for zip codes
        result = geocode_location(location_input)
        if result:
            return result

    # Treat as city name or address and geocode it
    result = geocode_location(location_input)
    if result:
        return result

    # If all else fails, return None
    return None


if __name__ == "__main__":
    # Test the geocoding function
    test_locations = ["10001", "New York, NY", "London", "40.7128,-74.0060"]  # NYC zip code  # NYC coordinates

    for loc in test_locations:
        coords = parse_location_input(loc)
        print(f"Location: {loc} -> Coordinates: {coords}")
