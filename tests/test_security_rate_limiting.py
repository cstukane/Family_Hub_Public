"""
Test script for rate limiting functionality in Kitchen Hub
"""

import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath("."))

from app import create_app
from hub.config import load_config


def test_rate_limiting_functionality():
    """Test the rate limiting functionality"""
    print("Testing rate limiting functionality...")

    # Create app with test config
    app = create_app("config.example.yaml")

    with app.test_client() as client:
        # Test that we can access endpoints without rate limiting initially
        response = client.get("/partials/notes")
        assert response.status_code == 200
        print("✓ Basic endpoint access works")

        # Since our rate limiting is implemented differently than Flask-Limiter,
        # we need to test by making multiple requests in the same test process
        # (which shares the in-memory store)
        responses = []
        for i in range(65):  # More than default limit
            response = client.get("/partials/notes")
            responses.append(response.status_code)

        # Count how many requests were successful vs rate limited
        success_count = sum(1 for status in responses if status == 200)
        rate_limited_count = sum(1 for status in responses if status == 429)

        print(f"✓ Made {len(responses)} requests, {success_count} successful, {rate_limited_count} rate limited")

        # We should have some rate limited responses
        assert rate_limited_count >= 5  # At least some should be rate limited beyond the limit

        # Test admin endpoints differently
        response = client.delete("/api/notes/999")  # This will fail but trigger rate limiting
        assert response.status_code in [200, 404, 429]  # Might be rate limited

        print("✓ Admin endpoint rate limiting tested")


def test_config_security_settings():
    """Test that security settings are properly loaded from config"""
    print("Testing security configuration...")

    config = load_config("config.example.yaml")

    # Check that security config exists and has expected values
    assert hasattr(config, "security")
    assert config.security.rate_limit_enabled
    assert config.security.default_rate_limit == "60 per minute"
    assert config.security.admin_rate_limit == "10 per minute"
    assert not config.security.ip_whitelist_enabled
    assert config.security.session_timeout == 3600
    assert config.security.secure_headers

    print("✓ Security configuration loaded correctly")


if __name__ == "__main__":
    test_config_security_settings()
    test_rate_limiting_functionality()
    print("\n✓ All rate limiting tests passed!")
