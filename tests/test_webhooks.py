"""Tests for webhook functionality."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from hub.services import webhook


class TestWebhookService:
    """Test cases for the webhook service."""

    def test_webhook_model_creation(self):
        """Test creating a webhook model."""
        webhook_obj = webhook.Webhook(
            name="Test Webhook", url="https://example.com/webhook", event_types=["weather_alert"], active=True
        )

        assert webhook_obj.name == "Test Webhook"
        assert webhook_obj.url == "https://example.com/webhook"
        assert webhook_obj.event_types == ["weather_alert"]
        assert webhook_obj.active is True
        assert webhook_obj.id is None

    def test_webhook_to_dict(self):
        """Test converting webhook to dictionary."""
        webhook_obj = webhook.Webhook(
            id=1,
            name="Test Webhook",
            url="https://example.com/webhook",
            event_types=["weather_alert", "severe_weather"],
            active=True,
        )

        result = webhook_obj.to_dict()
        assert result["id"] == 1
        assert result["name"] == "Test Webhook"
        assert result["url"] == "https://example.com/webhook"
        assert "weather_alert" in result["event_types"]
        assert "severe_weather" in result["event_types"]
        assert result["active"] is True

    def test_webhook_log_model_creation(self):
        """Test creating a webhook log model."""
        log = webhook.WebhookLog(id=1, webhook_id=1, payload={"test": "data"}, status="success", response="OK")

        assert log.id == 1
        assert log.webhook_id == 1
        assert log.payload == {"test": "data"}
        assert log.status == "success"
        assert log.response == "OK"

    def test_signature_generation(self):
        """Test webhook signature generation."""
        secret = "test-secret"
        payload = {"event_type": "weather_alert", "data": {"temp": 30}}

        # Test the signature generation function
        signature = webhook._generate_signature(secret, payload)

        # Should start with sha256=
        assert signature.startswith("sha256=")

        # Should be a proper hex digest
        hash_part = signature[7:]  # Remove "sha256=" prefix
        try:
            int(hash_part, 16)  # Try to parse as hex
            assert len(hash_part) == 64  # SHA256 produces 64 hex chars
        except ValueError:
            assert False, "Signature hash is not a valid hex string"


class TestWeatherAlertService:
    """Test cases for the weather alert service."""

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
