"""
Test script for voice commands functionality
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath("."))


def test_voice_service():
    """Test the voice service directly"""
    print("Testing voice service...")

    # Import the voice service and config
    from hub.config import load_config
    from hub.services.voice import get_available_commands, process_voice_command

    # Load the app config to pass to the voice processor
    config = load_config("config.example.yaml")
    apps_config = config.apps

    # Test available commands
    commands = get_available_commands()
    print(f"Available commands: {len(commands)} found")
    for cmd, desc in commands.items():
        print(f"  - {cmd}: {desc}")

    # Test various commands
    test_cases = [
        ("open youtube", "Should launch YouTube if app exists"),
        ("add milk to shopping list", "Should add item to shopping list"),
        ("add note buy groceries", "Should create a note"),
        ("switch to calendar", "Should switch to calendar view"),
        ("play music", "Should play music if music app exists"),
        ("help", "Should show help"),
        ("unknown command", "Should return error"),
    ]

    for command, description in test_cases:
        print(f"\nTesting command: '{command}' - {description}")
        result = process_voice_command(command, apps_config)
        print(f"Result: {result}")


def test_config():
    """Test that voice is enabled in config"""
    print("\nTesting configuration...")

    from hub.config import load_config

    config = load_config("config.example.yaml")

    voice_enabled = config.features.voice
    print(f"Voice feature enabled: {voice_enabled}")

    return voice_enabled


def main():
    print("Starting voice commands test...")

    # Test configuration
    voice_enabled = test_config()
    if not voice_enabled:
        print("Warning: Voice is not enabled in config. Tests may not function as expected.")

    # Test voice service
    test_voice_service()

    print("\nVoice commands test completed.")


if __name__ == "__main__":
    main()
