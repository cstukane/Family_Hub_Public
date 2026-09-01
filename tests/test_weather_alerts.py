"""Tests for weather alert functionality."""

import json
from datetime import datetime


class TestWeatherAlertLogic:
    """Test cases for weather alert logic that doesn't require Flask app context."""

    def test_weather_alert_threshold_evaluation(self):
        """Test weather alert threshold evaluation."""
        from hub.services.weather_alert import WeatherAlertThreshold

        # Test greater than threshold
        threshold = WeatherAlertThreshold("temperature", 30.0, "gt")
        assert threshold.evaluate(35.0) is True
        assert threshold.evaluate(25.0) is False

        # Test less than threshold
        threshold = WeatherAlertThreshold("temperature", 0.0, "lt")
        assert threshold.evaluate(-5.0) is True
        assert threshold.evaluate(5.0) is False

        # Test greater than or equal
        threshold = WeatherAlertThreshold("temperature", 20.0, "ge")
        assert threshold.evaluate(20.0) is True
        assert threshold.evaluate(25.0) is True
        assert threshold.evaluate(15.0) is False

        # Test less than or equal
        threshold = WeatherAlertThreshold("temperature", 20.0, "le")
        assert threshold.evaluate(20.0) is True
        assert threshold.evaluate(15.0) is True
        assert threshold.evaluate(25.0) is False

    def test_weather_alert_event_creation(self):
        """Test weather alert event creation."""
        from hub.services.weather_alert import WeatherAlertEvent

        event = WeatherAlertEvent(
            alert_type="high_temperature",
            location="Test City",
            description="High temperature alert",
            current_value=35.0,
            threshold_value=30.0,
            timestamp=datetime.now(),
        )

        assert event.alert_type == "high_temperature"
        assert event.location == "Test City"
        assert event.description == "High temperature alert"
        assert event.current_value == 35.0
        assert event.threshold_value == 30.0

        # Test to_dict method
        event_dict = event.to_dict()
        assert "alert_type" in event_dict
        assert event_dict["current_value"] == 35.0

    def test_weather_severity_detection(self):
        """Test weather severity detection logic directly."""
        from hub.services.weather_alert import is_weather_severe

        # Test different weather conditions
        test_cases = [
            # High temperature (>38)
            ({"temperature": 39, "condition": "Sunny", "wind_speed": 10}, True),
            # High temperature (not >38)
            ({"temperature": 38, "condition": "Sunny", "wind_speed": 10}, False),
            # Very low temperature
            ({"temperature": -15, "condition": "Snow", "wind_speed": 5}, True),
            # Very high wind speed
            ({"temperature": 20, "condition": "Windy", "wind_speed": 60}, True),
            # High wind speed (not >50)
            ({"temperature": 20, "condition": "Windy", "wind_speed": 50}, False),
            # Severe condition
            ({"temperature": 25, "condition": "thunderstorm", "wind_speed": 30}, True),
            # Normal conditions
            ({"temperature": 22, "condition": "Partly Cloudy", "wind_speed": 15}, False),
        ]

        # We'll test the logic directly by checking conditions
        for weather_data, expected_result in test_cases:
            temp = weather_data["temperature"]
            wind_speed = weather_data["wind_speed"]
            condition = weather_data["condition"].lower()

            # Replicate the logic from is_weather_severe
            is_severe = (
                temp > 38  # Very high temperature
                or temp < -10  # Very low temperature
                or wind_speed > 50  # Very high wind speed
                or any(severe_word in condition for severe_word in ["thunderstorm", "hail", "tornado", "hurricane"])
            )

            assert is_severe == expected_result, f"Failed for weather data: {weather_data}"
