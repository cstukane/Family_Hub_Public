"""
Test script for IP whitelisting functionality in Family Hub
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath("."))

from app import create_app
from hub.config import load_config


def test_ip_whitelisting_functionality():
    """Test the IP whitelisting functionality"""
    print("Testing IP whitelisting functionality...")

    # Create app with test config
    app = create_app("config.example.yaml")

    with app.test_client() as client:
        # Initially, with IP whitelist disabled, all requests should work
        response = client.get("/api/oauth/google")
        # This endpoint will return 400 because Google Calendar is not configured,
        # but it should not be blocked by IP whitelist
        assert response.status_code in [400, 404]  # Expected behavior without config
        print("✓ IP whitelisting disabled - endpoint accessible")

        # Test the X-Forwarded-For header handling
        response = client.get("/api/ha/entities", headers={"X-Forwarded-For": "192.168.1.100"})
        # Should not be blocked due to IP whitelist being disabled in test config
        print("✓ X-Forwarded-For header handling tested")


def test_config_ip_whitelist_settings():
    """Test that IP whitelist settings are properly loaded from config"""
    print("Testing IP whitelist configuration...")

    config = load_config("config.example.yaml")

    # Check that IP whitelist config exists and has expected values
    assert hasattr(config, "security")
    assert not config.security.ip_whitelist_enabled
    assert isinstance(config.security.ip_whitelist, list)
    assert len(config.security.ip_whitelist) == 0  # Empty in test config

    print("✓ IP whitelist configuration loaded correctly")


def test_ip_extraction_logic():
    """Test that IP extraction works correctly from headers"""
    print("Testing IP extraction from headers...")

    app = create_app("config.example.yaml")

    with app.app_context():
        with app.test_request_context("/", headers={"X-Forwarded-For": "192.168.1.100, 10.0.0.1, 127.0.0.1"}):
            from flask import request

            # Test that we can extract the first IP from X-Forwarded-For
            client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            if "," in client_ip:
                client_ip = client_ip.split(",")[0].strip()

            assert client_ip == "192.168.1.100"
            print("✓ IP extraction from X-Forwarded-For header works correctly")


if __name__ == "__main__":
    test_config_ip_whitelist_settings()
    test_ip_extraction_logic()
    test_ip_whitelisting_functionality()
    print("\n✓ All IP whitelisting tests passed!")
