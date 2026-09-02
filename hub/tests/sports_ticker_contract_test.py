"""
Unit tests for sports ticker data contract validation.
Ensures the 'headline-only' display contract is enforced.
"""

import json
import os
from datetime import datetime


def test_sports_ticker_headline_only_contract():
    """
    Validates that the sports ticker data follows the headline-only contract,
    meaning no play-by-play or detailed strings are included in the payload.
    """
    # Load the mock data
    mock_path = os.path.join(os.path.dirname(__file__), "..", "..", "static", "mock", "sports_ticker.json")
    with open(mock_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Verify structure
    assert "updated_at" in data  # nosec B101
    assert "meta" in data  # nosec B101
    assert "games" in data  # nosec B101
    assert isinstance(data["games"], list)  # nosec B101

    # Verify meta structure
    meta = data["meta"]
    assert "timezone" in meta  # nosec B101
    assert "cache_age_seconds" in meta  # nosec B101
    assert "stale" in meta  # nosec B101
    assert "favorites" in meta  # nosec B101
    assert "source" in meta  # nosec B101
    assert "fetch_error_reason" in meta  # nosec B101

    # Validate each game entry
    for game in data["games"]:
        # Verify required fields exist
        required_fields = ["id", "status", "home_team", "away_team", "home_score", "away_score"]
        for field in required_fields:
            assert field in game, f"Missing required field: {field}"  # nosec B101

        # Validate status is one of the allowed values
        assert game["status"] in ["scheduled", "in_progress", "final"], f"Invalid status: {game['status']}"  # nosec B101

        # Validate home and away team structures
        for team_key in ["home_team", "away_team"]:
            team = game[team_key]
            assert "name" in team  # nosec B101
            assert "abbreviation" in team  # nosec B101
            assert "score" in team  # nosec B101

        # Validate no play-by-play or detailed strings in basic fields
        # (These should not contain play-by-play info according to the contract)
        basic_display_fields = ["quarter", "time_remaining", "broadcast"]
        for field in basic_display_fields:
            if field in game and game[field] is not None:
                value = game[field]
                # Basic validation that these fields don't contain play-by-play style text
                assert isinstance(value, str), f"Field {field} should be a string"  # nosec B101

                # Check for common play-by-play indicators that shouldn't be in headline-only data
                play_by_play_indicators = [
                    "touchdown",
                    "home run",
                    "three pointer",
                    "goal",
                    "strike",
                    "foul",
                    "shot",
                    "pass",
                    "catch",
                    "save",
                    "assist",
                    "block",
                    "steal",
                    "injury",
                    "timeout",
                    "penalty",
                    "free throw",
                ]
                value_lower = value.lower()
                for indicator in play_by_play_indicators:
                    assert (  # nosec B101
                        indicator not in value_lower
                    ), f"Field {field} contains play-by-play content ('{indicator}'): {value}"

        # Validate team names and abbreviations don't contain detailed info
        for team_key in ["home_team", "away_team"]:
            team = game[team_key]
            if team["name"]:
                name_lower = team["name"].lower()
                # Check for play-by-play style content in team names
                for indicator in ["defensive", "offensive", "power play", "man down"]:
                    assert (  # nosec B101
                        indicator not in name_lower
                    ), f"Team {team_key} name contains detailed info ('{indicator}'): {team['name']}"

    print("All headline-only contract validations passed!")


def test_sports_ticker_schema_validation():
    """
    Validates the sports ticker data against the schema contract.
    """
    # Load the mock data
    mock_path = os.path.join(os.path.dirname(__file__), "..", "..", "static", "mock", "sports_ticker.json")
    with open(mock_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate updated_at format
    datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))

    # Validate each game
    for game in data["games"]:
        # Check if start_time fields are properly formatted when present
        if "start_time" in game and game["start_time"]:
            datetime.fromisoformat(game["start_time"])

        if "start_time_utc" in game and game["start_time_utc"]:
            datetime.fromisoformat(game["start_time_utc"].replace("Z", "+00:00"))

    print("All schema validations passed!")


if __name__ == "__main__":
    test_sports_ticker_headline_only_contract()
    test_sports_ticker_schema_validation()
    print("All tests passed!")
