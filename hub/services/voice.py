"""Voice command processing service for the Kitchen Hub."""

import re
from typing import Any, Dict, List

from . import media, notes, shopping


def process_voice_command(command: str, apps_config: List = None) -> Dict[str, Any]:
    """
    Process a voice command and execute the corresponding action.

    Args:
        command: The voice command string to process
        apps_config: List of app configurations (passed from the API endpoint)

    Returns:
        Dictionary with result of the command execution
    """
    if not command or not isinstance(command, str):
        return {"status": "error", "message": "Invalid command"}

    # Normalize the command string
    command = command.strip().lower()

    # Check for various command patterns
    result = _parse_command(command, apps_config or [])

    if result:
        return result
    else:
        return {"status": "error", "message": f"Command not recognized: {command}"}


def _parse_command(command: str, apps_config: List) -> Dict[str, Any]:
    """Parse the command and determine the appropriate action."""

    # Media launch commands (e.g., "open youtube", "launch spotify")
    for app in apps_config:
        app_label = app.label.lower()
        if f"open {app_label}" in command or f"launch {app_label}" in command or f"play {app_label}" in command:
            return _launch_media_app(app.id)

    # Shopping list commands
    # Add item: "add milk to shopping list", "add eggs to my shopping list"
    shopping_match = re.search(r"add\s+(.+?)\s+to\s+(?:my\s+)?shopping\s+list", command)
    if shopping_match:
        item_text = shopping_match.group(1).strip()
        return _add_to_shopping(item_text)

    # Notes commands
    # Add note: "add note remember to call mom", "create note buy groceries"
    note_match = re.search(r"(?:add\s+note|create\s+note|note)\s+(.+)", command)
    if note_match:
        note_text = note_match.group(1).strip()
        return _add_note(note_text)

    # Media play commands (e.g., "play music", "play a song")
    if "play" in command and ("music" in command or "song" in command):
        # Find a music app in the config
        for app in apps_config:
            if (
                any(keyword in app.label.lower() for keyword in ["spotify", "music", "youtube"])
                and app.action == "open_iframe"
            ):
                return _launch_media_app(app.id)

    # Calendar commands
    if "calendar" in command:
        return _switch_view("week_calendar")

    # Weather commands
    if "weather" in command or "forecast" in command:
        return _switch_view("weather")

    # Help commands
    if "help" in command:
        return _get_help()

    # If no pattern matched, return None to indicate command not recognized
    return None


def _launch_media_app(app_id: str) -> Dict[str, Any]:
    """Launch a media app by ID."""
    try:
        result = media.launch_app(app_id)
        if "error" in result:
            return {"status": "error", "message": result["error"]}

        return {"status": "success", "message": f"Launched {app_id}", "action": "media_launch", "app_id": app_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _add_to_shopping(item_text: str) -> Dict[str, Any]:
    """Add an item to the shopping list."""
    try:
        # Create the shopping item
        item = shopping.create_shopping_item(item_text)
        return {
            "status": "success",
            "message": f"Added '{item_text}' to shopping list",
            "item_id": item.id,
            "action": "shopping_add",
            "item_text": item_text,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _add_note(note_text: str) -> Dict[str, Any]:
    """Add a note."""
    try:
        note = notes.create_note(note_text)
        return {
            "status": "success",
            "message": f"Added note: {note_text}",
            "note_id": note.id,
            "action": "note_add",
            "note_text": note_text,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _switch_view(view_name: str) -> Dict[str, Any]:
    """Switch the current view."""
    return {
        "status": "success",
        "message": f"Switching to {view_name}",
        "action": "view_switch",
        "view_name": view_name,
    }


def _get_help() -> Dict[str, Any]:
    """Return help information for available voice commands."""
    help_text = (
        "Available voice commands: "
        "Open [app name] to launch media apps (e.g., 'open youtube'), "
        "Add [item] to shopping list, "
        "Add note [note text], "
        "Switch to calendar or weather view, "
        "Play music to play music apps"
    )
    return {"status": "success", "message": help_text, "action": "help"}


def get_available_commands() -> Dict[str, str]:
    """Get a dictionary of available voice commands and their descriptions."""
    return {
        "open [app_name]": "Launch a media application (e.g., 'open youtube', 'open spotify')",
        "add [item] to shopping list": "Add an item to the shopping list (e.g., 'add milk to shopping list')",
        "add note [text]": "Create a new note (e.g., 'add note remember meeting at 3pm')",
        "switch to [view]": "Switch to a view (e.g., 'switch to calendar', 'switch to weather')",
        "play music": "Play music using the configured music app",
        "help": "Show available voice commands",
    }
