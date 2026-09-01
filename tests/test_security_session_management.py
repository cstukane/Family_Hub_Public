"""
Test script for session management functionality in Family Hub
"""

import os
import sys
from datetime import timedelta

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath("."))

from app import create_app


def test_session_configuration():
    """Test that session settings are properly configured"""
    print("Testing session configuration...")

    app = create_app("config.example.yaml")

    # Check session configuration values
    assert app.config.get("SESSION_COOKIE_SECURE"), "Session cookie should be secure"
    assert app.config.get("SESSION_COOKIE_HTTPONLY"), "Session cookie should be HTTP only"
    assert app.config.get("SESSION_COOKIE_SAMESITE") == "Lax", "Session cookie should have SameSite=Lax"

    # Check session timeout (PERMANENT_SESSION_LIFETIME should be set to the security timeout value)
    expected_timeout = timedelta(seconds=3600)  # From config.security.session_timeout
    assert app.config.get("PERMANENT_SESSION_LIFETIME") == expected_timeout, "Session timeout should match config"

    print("✓ Session configuration values are correct")


def test_secret_key_configuration():
    """Test that secret key is configured"""
    print("Testing secret key configuration...")

    app = create_app("config.example.yaml")

    # Check that secret key is set
    assert app.secret_key is not None, "Secret key should be set"
    assert isinstance(app.secret_key, (str, bytes)), "Secret key should be string or bytes"

    print("✓ Secret key is configured")


def test_session_security_features():
    """Test that session security features are enabled"""
    print("Testing session security features...")

    app = create_app("config.example.yaml")

    # Verify the security-sensitive settings
    session_settings = {
        "SESSION_COOKIE_SECURE": app.config.get("SESSION_COOKIE_SECURE"),
        "SESSION_COOKIE_HTTPONLY": app.config.get("SESSION_COOKIE_HTTPONLY"),
        "SESSION_COOKIE_SAMESITE": app.config.get("SESSION_COOKIE_SAMESITE"),
    }

    assert session_settings["SESSION_COOKIE_SECURE"], "Secure flag should be set for session cookies"
    assert session_settings["SESSION_COOKIE_HTTPONLY"], "HTTPOnly flag should be set for session cookies"
    assert session_settings["SESSION_COOKIE_SAMESITE"] in [
        "Lax",
        "Strict",
    ], "SameSite should be set for session cookies"

    print("✓ Session security features are enabled")


if __name__ == "__main__":
    test_secret_key_configuration()
    test_session_configuration()
    test_session_security_features()
    print("\n✓ All session management tests passed!")
