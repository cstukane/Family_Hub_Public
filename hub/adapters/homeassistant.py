"""Home Assistant adapter for entity state and service calls."""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from hub.cache import get_cache, set_cache
from hub.utils.http import RateLimitError, rate_limited_get, rate_limited_post

logger = logging.getLogger(__name__)


class HomeAssistantAdapter:
    """Adapter for interacting with Home Assistant API."""

    def __init__(self, base_url: str, access_token: str):
        """
        Initialize the Home Assistant adapter.

        Args:
            base_url: Base URL of the Home Assistant instance (e.g., http://localhost:8123)
            access_token: Long-lived access token for Home Assistant
        """
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    def get_entity_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the state of a specific entity.

        Args:
            entity_id: Entity ID (e.g., 'light.living_room', 'switch.outdoor_light')
        Returns:
            Dictionary containing entity state information or None if failed
        """
        # Create cache key
        cache_key = f"ha:state:{entity_id}"

        # Try to get from cache first
        cached_data = get_cache(cache_key)
        if cached_data:
            return cached_data

        try:
            url = urljoin(self.base_url, f"/api/states/{entity_id}")
            response = rate_limited_get(url, headers=self.headers, timeout=10, service_name="homeassistant")

            if response.status_code == 200:
                data = response.json()

                # Cache for 30 seconds
                set_cache(cache_key, data, ttl_seconds=30)

                return data
            else:
                logger.error("Error getting entity state: %s - %s", response.status_code, response.text)
                return None
        except RateLimitError as e:
            logger.warning("Home Assistant rate limited: %s", e)
            return None
        except requests.exceptions.RequestException:
            logger.exception("Error getting entity state")
            return None
        except Exception:
            logger.exception("Error getting entity state")
            return None

    def get_entities(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all entities or entities filtered by domain.

        Args:
            domain: Optional domain to filter (e.g., 'light', 'switch', 'sensor')
        Returns:
            List of entity state dictionaries
        """
        # Create cache key
        cache_key = f"ha:entities:{domain or 'all'}"

        # Try to get from cache first
        cached_data = get_cache(cache_key)
        if cached_data:
            return cached_data

        try:
            url = urljoin(self.base_url, "/api/states")
            response = rate_limited_get(url, headers=self.headers, timeout=10, service_name="homeassistant")

            if response.status_code == 200:
                all_entities = response.json()

                # Filter by domain if specified
                if domain:
                    filtered_entities = [
                        entity for entity in all_entities if entity["entity_id"].startswith(f"{domain}.")
                    ]
                    entities = filtered_entities
                else:
                    entities = all_entities

                # Cache for 60 seconds
                set_cache(cache_key, entities, ttl_seconds=60)

                return entities
            else:
                logger.error("Error getting entities: %s - %s", response.status_code, response.text)
                return []
        except RateLimitError as e:
            logger.warning("Home Assistant rate limited: %s", e)
            return []
        except requests.exceptions.RequestException:
            logger.exception("Error getting entities")
            return []
        except Exception:
            logger.exception("Error getting entities")
            return []

    def call_service(self, domain: str, service: str, service_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Call a Home Assistant service.

        Args:
            domain: Domain of the service (e.g., 'light', 'switch', 'script')
            service: Service name (e.g., 'turn_on', 'turn_off', 'toggle')
            service_data: Optional data to send with the service call
        Returns:
            True if the service call was successful, False otherwise
        """
        try:
            url = urljoin(self.base_url, f"/api/services/{domain}/{service}")
            payload = {"entity_id": service_data.get("entity_id") if service_data else None}

            # Add any additional service data
            if service_data:
                for key, value in service_data.items():
                    if key != "entity_id":  # entity_id is handled separately
                        payload[key] = value

            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            response = rate_limited_post(
                url, headers=self.headers, json=payload, timeout=10, service_name="homeassistant"
            )

            if response.status_code in [200, 201]:
                return True
            else:
                logger.error("Error calling service: %s - %s", response.status_code, response.text)
                return False
        except RateLimitError as e:
            logger.warning("Home Assistant rate limited: %s", e)
            return False
        except requests.exceptions.RequestException:
            logger.exception("Error calling service")
            return False
        except Exception:
            logger.exception("Error calling service")
            return False

    def get_area_entities(self, area_id: str) -> List[Dict[str, Any]]:
        """
        Get all entities in a specific area.

        Args:
            area_id: ID of the area to get entities for
        Returns:
            List of entity state dictionaries in the area
        """
        # Get all entities
        all_entities = self.get_entities()

        # Fetch areas to match entity area with area_id
        try:
            url = urljoin(self.base_url, "/api/areas")
            response = rate_limited_get(url, headers=self.headers, timeout=10, service_name="homeassistant")

            if response.status_code == 200:
                # Filter entities based on area
                area_entities = []
                for entity in all_entities:
                    entity_area_id = entity.get("attributes", {}).get("area_id")
                    if entity_area_id == area_id:
                        area_entities.append(entity)

                return area_entities
            else:
                logger.error("Error getting areas: %s - %s", response.status_code, response.text)
                # Fallback to returning all entities if area lookup fails
                return all_entities
        except RateLimitError as e:
            logger.warning("Home Assistant rate limited: %s", e)
            return all_entities
        except requests.exceptions.RequestException:
            logger.exception("Error getting areas")
            # Fallback to returning all entities if area lookup fails
            return all_entities
        except Exception:
            logger.exception("Error getting areas")
            # Fallback to returning all entities if area lookup fails
            return all_entities


def initialize_ha_adapter(config: Dict[str, Any]) -> Optional[HomeAssistantAdapter]:
    """
    Initialize and return a Home Assistant adapter based on configuration.

    Args:
        config: Home Assistant configuration containing base_url and access_token
    Returns:
        HomeAssistantAdapter instance or None if configuration is invalid
    """
    if not config or not config.get("base_url") or not config.get("access_token"):
        return None

    try:
        adapter = HomeAssistantAdapter(base_url=config["base_url"], access_token=config["access_token"])
        return adapter
    except Exception:
        logger.exception("Error initializing Home Assistant adapter")
        return None
