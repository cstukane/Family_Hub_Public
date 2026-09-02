"""Unit tests for the sports ticker service."""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from hub.models import Game, SportsData, Team
from hub.services.sports_ticker_service import (
    _format_phase_label,
    _normalize_status,
    fetch_sports_data_with_resilience,
    get_sports_ticker_data,
    transform_to_ticker_contract,
)


class TestSportsTickerService(unittest.TestCase):
    """Test cases for the sports ticker service functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.home_team = Team(name="Los Angeles Lakers", abbreviation="LAL", id="14")
        self.away_team = Team(name="Golden State Warriors", abbreviation="GSW", id="11")

        self.sample_game = Game(
            id="401234567",
            home_team=self.home_team,
            away_team=self.away_team,
            home_score=112,
            away_score=108,
            status="final",
            start_time=datetime(2024, 1, 15, 19, 30, tzinfo=timezone.utc),
            quarter="Final",
            time_remaining=None,
            venue="Crypto.com Arena",
            broadcast="TNT",
        )

        self.sample_sports_data = SportsData(
            games=[self.sample_game], last_updated=datetime(2024, 1, 15, 23, 30, tzinfo=timezone.utc), source="espn"
        )

    def test_transform_to_ticker_contract_basic_structure(self):
        """Test that the transformed data has the correct basic structure."""
        result = transform_to_ticker_contract(self.sample_sports_data, ["LAL", "GSW"])

        # Check top-level structure
        self.assertIn("updated_at", result)
        self.assertIn("meta", result)
        self.assertIn("games", result)

        # Check meta structure
        meta = result["meta"]
        self.assertIn("timezone", meta)
        self.assertIn("cache_age_seconds", meta)
        self.assertIn("stale", meta)
        self.assertIn("favorites", meta)
        self.assertIn("source", meta)
        self.assertIn("fetch_error_reason", meta)

        # Check games structure
        games = result["games"]
        self.assertEqual(len(games), 1)

        game = games[0]
        self.assertIn("id", game)
        self.assertIn("league", game)
        self.assertIn("status", game)
        self.assertIn("start_time", game)
        self.assertIn("start_time_utc", game)
        self.assertIn("time_remaining", game)
        self.assertIn("quarter", game)
        self.assertIn("home_team", game)
        self.assertIn("away_team", game)
        self.assertIn("home_score", game)
        self.assertIn("away_score", game)
        self.assertIn("broadcast", game)
        self.assertIn("source_url", game)

    def test_transform_to_ticker_contract_game_fields(self):
        """Test that game fields are properly transformed."""
        result = transform_to_ticker_contract(self.sample_sports_data, ["LAL", "GSW"])

        game = result["games"][0]

        # Check specific field values
        self.assertEqual(game["id"], "401234567")
        self.assertEqual(game["status"], "final")
        self.assertEqual(game["home_score"], 112)
        self.assertEqual(game["away_score"], 108)
        self.assertEqual(game["quarter"], "Final")

        # Check team structures
        self.assertEqual(game["home_team"]["name"], "Los Angeles Lakers")
        self.assertEqual(game["home_team"]["abbreviation"], "LAL")
        self.assertEqual(game["home_team"]["score"], 112)

        self.assertEqual(game["away_team"]["name"], "Golden State Warriors")
        self.assertEqual(game["away_team"]["abbreviation"], "GSW")
        self.assertEqual(game["away_team"]["score"], 108)

        # Check start time format
        self.assertIsNotNone(game["start_time"])
        self.assertIsNotNone(game["start_time_utc"])

    def test_normalize_status_mappings(self):
        """Test that ESPN status strings are properly normalized."""
        # Test final/completed statuses
        self.assertEqual(_normalize_status("STATUS_FINAL"), "final")
        self.assertEqual(_normalize_status("STATUS_COMPLETED"), "final")
        self.assertEqual(_normalize_status("STATUS_CLOSING"), "final")

        # Test in-progress/live statuses
        self.assertEqual(_normalize_status("STATUS_IN_PROGRESS"), "in_progress")
        self.assertEqual(_normalize_status("STATUS_LIVE"), "in_progress")
        self.assertEqual(_normalize_status("STATUS_IN_COUNTDOWN"), "in_progress")

        # Test scheduled statuses
        self.assertEqual(_normalize_status("STATUS_SCHEDULED"), "scheduled")
        self.assertEqual(_normalize_status("STATUS_PRE_GAME"), "scheduled")
        self.assertEqual(_normalize_status("STATUS_TBD"), "scheduled")

        # Test unknown status (should default to scheduled)
        self.assertEqual(_normalize_status("STATUS_UNKNOWN"), "scheduled")
        self.assertEqual(_normalize_status("STATUS_INVALID"), "scheduled")

    def test_format_phase_label_for_core_live_sports(self):
        """League-specific live labels should stay compact and reader-friendly."""
        self.assertEqual(_format_phase_label("nba", 3, ""), "Q3")
        self.assertEqual(_format_phase_label("nfl", 2, ""), "Q2")
        self.assertEqual(_format_phase_label("nhl", 3, ""), "3rd")
        self.assertEqual(_format_phase_label("mlb", 8, "Bot 8th"), "Bot 8th")

    def test_format_phase_label_uses_feed_detail_for_soccer_and_unknown_leagues(self):
        """Feeds that already provide a good live label should pass it through."""
        self.assertEqual(_format_phase_label("soccer", None, "45'+2"), "45'+2")
        self.assertEqual(_format_phase_label("epl", None, "HT"), "HT")

    def test_transform_to_ticker_contract_favorites(self):
        """Test that favorites are properly included in the meta."""
        result = transform_to_ticker_contract(self.sample_sports_data, ["LAL", "BOS"])

        self.assertEqual(result["meta"]["favorites"], ["LAL", "BOS"])
        self.assertEqual(result["meta"]["source"], "espn")

    def test_transform_to_ticker_contract_stale_flag(self):
        """Test that stale flag is set based on cache age."""
        # For this test, we'll check that the function doesn't error and includes the stale flag
        result = transform_to_ticker_contract(self.sample_sports_data, ["LAL"])

        self.assertIn("stale", result["meta"])
        self.assertIsInstance(result["meta"]["stale"], bool)

    def test_transform_handles_missing_data_gracefully(self):
        """Test that the transformation handles missing or None values gracefully."""
        # Create a game with some missing data
        game_with_missing_data = Game(
            id="",
            home_team=Team(name="Team A", abbreviation="", id=""),
            away_team=Team(name="Team B", abbreviation="", id=""),
            home_score=0,
            away_score=0,
            status="scheduled",
            start_time=None,
            quarter=None,
            time_remaining=None,
            venue=None,
            broadcast=None,
        )

        sports_data_with_missing = SportsData(
            games=[game_with_missing_data], last_updated=datetime.now(timezone.utc), source="espn"
        )

        result = transform_to_ticker_contract(sports_data_with_missing, [])

        # Should not raise exceptions and should have proper structure
        self.assertEqual(len(result["games"]), 1)
        game = result["games"][0]

        # Check that missing data is handled properly
        self.assertEqual(game["id"], "")
        self.assertIsNone(game["start_time"])  # Should be None when input is None
        self.assertEqual(game["quarter"], None)
        self.assertEqual(game["time_remaining"], None)

    @patch("hub.services.sports_ticker_service._make_request_with_backoff")
    def test_fetch_sports_data_with_resilience(self, mock_make_request):
        """Test that the fetch function handles successful response."""
        now = datetime.now(timezone.utc).replace(microsecond=0)

        # Mock a successful response
        mock_response = {
            "events": [
                {
                    "id": "401234567",
                    "status": {"type": {"name": "STATUS_FINAL"}},
                    "date": now.isoformat().replace("+00:00", "Z"),
                    "competitions": [
                        {
                            "competitors": [
                                {
                                    "homeAway": "home",
                                    "team": {"displayName": "Lakers", "abbreviation": "LAL"},
                                    "score": "112",
                                },
                                {
                                    "homeAway": "away",
                                    "team": {"displayName": "Warriors", "abbreviation": "GSW"},
                                    "score": "108",
                                },
                            ],
                            "status": {"period": "Final", "displayClock": ""},
                        }
                    ],
                    "links": [{"href": "https://www.espn.com/game/_/gameId/401234567"}],
                }
            ]
        }
        mock_make_request.return_value = mock_response

        result = fetch_sports_data_with_resilience("nba")

        # Check that the result is processed correctly
        self.assertIsNotNone(result)
        self.assertIn("events", result)
        self.assertEqual(len(result["events"]), 1)

        event = result["events"][0]
        self.assertEqual(event["id"], "401234567")
        self.assertEqual(event["status"], "final")  # Should be normalized
        self.assertEqual(event["home_team"]["abbreviation"], "LAL")
        self.assertEqual(event["away_score"], 108)

    @patch("hub.services.sports_ticker_service._make_request_with_backoff")
    def test_fetch_sports_data_with_resilience_formats_mlb_inning_clock(self, mock_make_request):
        """Live MLB games should expose inning details for ticker rendering."""
        now = datetime.now(timezone.utc).replace(microsecond=0)

        mock_response = {
            "events": [
                {
                    "id": "401999999",
                    "status": {"type": {"name": "STATUS_IN_PROGRESS"}},
                    "date": now.isoformat().replace("+00:00", "Z"),
                    "competitions": [
                        {
                            "competitors": [
                                {
                                    "homeAway": "home",
                                    "team": {"displayName": "Marlins", "abbreviation": "MIA"},
                                    "score": "4",
                                },
                                {
                                    "homeAway": "away",
                                    "team": {"displayName": "Rays", "abbreviation": "TB"},
                                    "score": "1",
                                },
                            ],
                            "status": {
                                "period": 5,
                                "displayClock": "Top 5th",
                                "type": {"state": "in", "shortDetail": "Top 5th"},
                            },
                        }
                    ],
                }
            ]
        }
        mock_make_request.return_value = mock_response

        result = fetch_sports_data_with_resilience("mlb")

        event = result["events"][0]
        self.assertEqual(event["status"], "in_progress")
        self.assertEqual(event["time_remaining"], "Top 5th")


if __name__ == "__main__":
    unittest.main()
