"""Weather alert service for monitoring and triggering alerts based on weather conditions."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import current_app

from hub.adapters.weather_openmeteo import get_current_weather
from hub.db import get_db
from hub.services.webhook import trigger_webhooks_for_event
from hub.utils.config_helpers import get_config_value


class WeatherAlertThreshold:
    """Class representing weather alert thresholds."""

    def __init__(self, condition: str, threshold_value: float, comparison: str = "gt"):
        """
        Initialize a weather alert threshold.

        Args:
            condition: Weather condition to monitor (temperature, humidity, wind_speed)
            threshold_value: Value to compare against
            comparison: Comparison operator ('gt', 'lt', 'ge', 'le', 'eq', 'ne')
        """
        self.condition = condition
        self.threshold_value = threshold_value
        self.comparison = comparison  # gt, lt, ge, le, eq, ne

    def evaluate(self, current_value: float) -> bool:
        """Evaluate if current weather value meets the threshold."""
        if self.comparison == "gt":
            return current_value > self.threshold_value
        elif self.comparison == "lt":
            return current_value < self.threshold_value
        elif self.comparison == "ge":
            return current_value >= self.threshold_value
        elif self.comparison == "le":
            return current_value <= self.threshold_value
        elif self.comparison == "eq":
            return current_value == self.threshold_value
        elif self.comparison == "ne":
            return current_value != self.threshold_value
        else:
            return False


class WeatherAlertEvent:
    """Class representing a weather alert event."""

    def __init__(
        self,
        alert_type: str,
        location: str,
        description: str,
        current_value: float,
        threshold_value: float,
        timestamp: datetime,
    ):
        self.alert_type = alert_type
        self.location = location
        self.description = description
        self.current_value = current_value
        self.threshold_value = threshold_value
        self.timestamp = timestamp

    def to_dict(self) -> Dict:
        """Convert to dictionary for webhook payload."""
        return {
            "alert_type": self.alert_type,
            "location": self.location,
            "description": self.description,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "timestamp": self.timestamp.isoformat(),
        }


def get_weather_alert_thresholds() -> List[Dict]:
    """Get configured weather alert thresholds from config."""
    config = current_app.config.get("CONFIG")
    if not config:
        return []

    # Get weather thresholds from config (if configured)
    # Default thresholds if not configured
    default_thresholds = [
        {
            "condition": "temperature",
            "threshold_value": 35.0,  # High temperature alert
            "comparison": "gt",
            "alert_type": "high_temperature",
            "description": "High temperature alert",
        },
        {
            "condition": "temperature",
            "threshold_value": 0.0,  # Freezing temperature alert
            "comparison": "lt",
            "alert_type": "freezing_temperature",
            "description": "Freezing temperature alert",
        },
        {
            "condition": "wind_speed",
            "threshold_value": 30.0,  # High wind alert
            "comparison": "gt",
            "alert_type": "high_wind",
            "description": "High wind alert",
        },
        {
            "condition": "humidity",
            "threshold_value": 80.0,  # High humidity alert
            "comparison": "gt",
            "alert_type": "high_humidity",
            "description": "High humidity alert",
        },
    ]

    # If the config has a weather.alerts section, use those instead
    weather_alerts = get_config_value(config, ("providers", "weather", "alerts"))
    if weather_alerts:
        return weather_alerts

    return default_thresholds


def check_weather_alerts() -> List[WeatherAlertEvent]:
    """Check current weather against configured thresholds and return triggered alerts."""
    current_weather = get_current_weather_data()
    if not current_weather:
        current_app.logger.error("Could not get current weather data for alert checking")
        return []

    thresholds = get_weather_alert_thresholds()
    triggered_alerts = []

    for threshold_config in thresholds:
        try:
            # Get the current weather value for this condition
            if threshold_config["condition"] == "temperature":
                current_value = current_weather.get("temperature", 0)
            elif threshold_config["condition"] == "humidity":
                current_value = current_weather.get("humidity", 0)
            elif threshold_config["condition"] == "wind_speed":
                current_value = current_weather.get("wind_speed", 0)
            else:
                continue  # Skip unknown conditions

            # Create threshold and evaluate
            threshold = WeatherAlertThreshold(
                condition=threshold_config["condition"],
                threshold_value=threshold_config["threshold_value"],
                comparison=threshold_config["comparison"],
            )

            if threshold.evaluate(current_value):
                # Create alert event
                alert_event = WeatherAlertEvent(
                    alert_type=threshold_config["alert_type"],
                    location=current_weather.get("location", "Unknown"),
                    description=threshold_config["description"],
                    current_value=current_value,
                    threshold_value=threshold_config["threshold_value"],
                    timestamp=datetime.now(),
                )

                triggered_alerts.append(alert_event)
        except Exception as e:
            current_app.logger.error(f"Error processing weather alert threshold: {e}")
            continue

    return triggered_alerts


def get_current_weather_data() -> Optional[Dict]:
    """Get current weather data from the configured provider."""
    try:
        config = current_app.config.get("CONFIG")
        weather_location = get_config_value(config, ("providers", "weather", "location"))
        if not weather_location:
            current_app.logger.error("Weather configuration not available")
            return None

        lat = getattr(weather_location, "lat", None)
        lon = getattr(weather_location, "lon", None)
        if isinstance(weather_location, dict):
            lat = weather_location.get("lat", lat)
            lon = weather_location.get("lon", lon)
        if lat is None or lon is None:
            current_app.logger.error("Weather location missing latitude/longitude")
            return None

        current = get_current_weather(lat, lon)
        return current
    except Exception as e:
        current_app.logger.error(f"Error getting current weather: {e}")
        return None


def process_weather_alerts() -> Dict[str, Any]:
    """Process weather alerts and trigger webhooks if thresholds are exceeded."""
    triggered_alerts = check_weather_alerts()

    if not triggered_alerts:
        # Log that no alerts were triggered
        current_app.logger.info("Weather alert check completed - no alerts triggered")
        return {"status": "no_alerts", "message": "No weather thresholds were exceeded", "alert_count": 0, "alerts": []}

    # Log the triggered alerts
    for alert in triggered_alerts:
        current_app.logger.info(f"Weather alert triggered: {alert.alert_type} - {alert.description}")

        # Log the alert to the database
        log_weather_alert(alert)

    # Trigger webhooks for weather alerts
    webhook_trigger_count = 0
    for alert in triggered_alerts:
        payload = {"event_type": "weather_alert", "data": alert.to_dict()}

        # Trigger all webhooks configured for weather alerts
        count = trigger_webhooks_for_event("weather_alert", payload, async_dispatch=True)
        webhook_trigger_count += count

        # Also trigger webhooks for specific alert type
        trigger_webhooks_for_event(alert.alert_type, payload, async_dispatch=True)

    current_app.logger.info(
        f"Weather alert processing completed - {len(triggered_alerts)} alerts, {webhook_trigger_count} webhooks triggered"
    )

    return {
        "status": "alerts_triggered",
        "message": f"{len(triggered_alerts)} weather alerts triggered",
        "alert_count": len(triggered_alerts),
        "webhook_count": webhook_trigger_count,
        "alerts": [alert.to_dict() for alert in triggered_alerts],
    }


def log_weather_alert(alert: WeatherAlertEvent) -> bool:
    """Log a weather alert to the database."""
    try:
        db = get_db()

        query = """
            INSERT INTO weather_alerts
            (alert_type, location, description, current_value, threshold_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """

        db.execute(
            query,
            (
                alert.alert_type,
                alert.location,
                alert.description,
                alert.current_value,
                alert.threshold_value,
                alert.timestamp,
            ),
        )
        db.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error logging weather alert: {e}")
        return False


def get_weather_alert_history(hours: int = 24) -> List[Dict]:
    """Get weather alert history for the specified number of hours."""
    try:
        db = get_db()

        since_time = datetime.now() - timedelta(hours=hours)

        query = """
            SELECT * FROM weather_alerts
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """

        rows = db.execute(query, (since_time,)).fetchall()

        alerts = []
        for row in rows:
            alerts.append(
                {
                    "id": row["id"],
                    "alert_type": row["alert_type"],
                    "location": row["location"],
                    "description": row["description"],
                    "current_value": row["current_value"],
                    "threshold_value": row["threshold_value"],
                    "timestamp": row["timestamp"],
                }
            )

        return alerts
    except Exception as e:
        current_app.logger.error(f"Error getting weather alert history: {e}")
        return []


def get_active_weather_alerts() -> List[Dict]:
    """Get active weather alerts (last 1 hour)."""
    return get_weather_alert_history(hours=1)


def is_weather_severe() -> bool:
    """Check if current weather is severe based on thresholds."""
    # Get current weather data
    current_weather = get_current_weather_data()
    if not current_weather:
        return False

    # Define what constitutes "severe" weather
    temperature = current_weather.get("temperature", 0)
    wind_speed = current_weather.get("wind_speed", 0)
    condition = current_weather.get("condition", "").lower()

    # Check for severe conditions
    is_severe = (
        temperature > 38  # Very high temperature
        or temperature < -10  # Very low temperature
        or wind_speed > 50  # Very high wind speed
        or any(severe_word in condition for severe_word in ["thunderstorm", "hail", "tornado", "hurricane"])
    )

    return is_severe
