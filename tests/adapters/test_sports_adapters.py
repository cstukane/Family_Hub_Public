"""Tests for sports adapters."""

from unittest.mock import Mock, patch

import pytest
import requests

from hub.adapters.sports_espn import ESPNAdapter
from hub.adapters.sports_thesportsdb import TheSportsDBAdapter


class TestTheSportsDBAdapter:
    """Test the TheSportsDB adapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = TheSportsDBAdapter(api_key="test_key")
        assert adapter.api_key == "test_key"
        assert adapter.base_url == "https://www.thesportsdb.com/api/v1/json"

        adapter_no_key = TheSportsDBAdapter()
        assert adapter_no_key.api_key is None

    @patch("hub.adapters.sports_thesportsdb.rate_limited_get")
    def test_make_request_with_api_key(self, mock_get):
        """Test making a request with API key."""
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        adapter = TheSportsDBAdapter(api_key="test_key")
        adapter._make_request("test_endpoint")

        mock_get.assert_called_once()
        # Check that the API key was included in parameters
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        assert call_args.kwargs["params"]["api_key"] == "test_key"

    @patch("hub.adapters.sports_thesportsdb.rate_limited_get")
    def test_make_request_without_api_key(self, mock_get):
        """Test making a request without API key."""
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        adapter = TheSportsDBAdapter()
        adapter._make_request("test_endpoint")

        mock_get.assert_called_once()
        # Check that the API key was not included in parameters
        call_args = mock_get.call_args
        if "params" in call_args.kwargs:
            assert "api_key" not in call_args.kwargs["params"]

    @patch("hub.adapters.sports_thesportsdb.rate_limited_get")
    def test_make_request_error(self, mock_get):
        """Test handling request errors."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        adapter = TheSportsDBAdapter()
        result = adapter._make_request("test_endpoint")

        assert result is None

    def test_parse_team(self):
        """Test parsing team data."""
        adapter = TheSportsDBAdapter()
        team_data = {
            "idTeam": "123",
            "strTeam": "Test Team",
            "strTeamShort": "TT",
            "strTeamBadge": "http://example.com/badge.png",
        }

        team = adapter._parse_team(team_data)

        assert team.id == "123"
        assert team.name == "Test Team"
        assert team.abbreviation == "TT"
        assert team.logo_url == "http://example.com/badge.png"

    def test_parse_game(self):
        """Test parsing game data."""
        adapter = TheSportsDBAdapter()
        event_data = {
            "idEvent": "456",
            "idHomeTeam": "home_123",
            "idAwayTeam": "away_456",
            "strHomeTeam": "Home Team",
            "strAwayTeam": "Away Team",
            "strHomeTeamShort": "HT",
            "strAwayTeamShort": "AT",
            "intHomeScore": "3",
            "intAwayScore": "2",
            "strStatus": "Finished",
            "dateEvent": "2023-10-01",
            "strTime": "15:00:00",
            "strVenue": "Test Stadium",
            "strTVStation": "ESPN",
        }

        game = adapter._parse_game(event_data)

        assert game.id == "456"
        assert game.home_team.name == "Home Team"
        assert game.away_team.name == "Away Team"
        assert game.home_score == 3
        assert game.away_score == 2
        assert game.status == "final"
        assert game.venue == "Test Stadium"
        assert game.broadcast == "ESPN"


class TestESPNAdapter:
    """Test the ESPN adapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = ESPNAdapter()
        assert adapter.base_url == "http://site.api.espn.com/apis/site/v2/sports"

    @patch("hub.adapters.sports_espn.rate_limited_get")
    def test_make_request(self, mock_get):
        """Test making a request."""
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        adapter = ESPNAdapter()
        adapter._make_request("basketball/nba/scoreboard")

        expected_url = f"{adapter.base_url}/basketball/nba/scoreboard"
        mock_get.assert_called_once_with(expected_url, timeout=10, service_name="espn")

    @patch("hub.adapters.sports_espn.rate_limited_get")
    def test_make_request_error(self, mock_get):
        """Test handling request errors."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        adapter = ESPNAdapter()
        result = adapter._make_request("basketball/nba/scoreboard")

        assert result is None

    def test_parse_team(self):
        """Test parsing team data."""
        adapter = ESPNAdapter()
        team_data = {
            "id": "123",
            "displayName": "Test Team",
            "abbreviation": "TT",
            "logo": "http://example.com/logo.png",
        }

        team = adapter._parse_team(team_data)

        assert team.id == "123"
        assert team.name == "Test Team"
        assert team.abbreviation == "TT"
        assert team.logo_url == "http://example.com/logo.png"

    def test_parse_game(self):
        """Test parsing game data."""
        adapter = ESPNAdapter()
        event_data = {
            "id": "789",
            "date": "2023-10-01T15:00:00Z",
            "competitions": [
                {
                    "competitors": [
                        {
                            "homeAway": "home",
                            "team": {"id": "home_123", "displayName": "Home Team", "abbreviation": "HT"},
                            "score": "3",
                        },
                        {
                            "homeAway": "away",
                            "team": {"id": "away_456", "displayName": "Away Team", "abbreviation": "AT"},
                            "score": "2",
                        },
                    ],
                    "status": {"type": {"name": "STATUS_FINAL"}, "period": 4, "displayClock": "0:00"},
                    "venue": {"fullName": "Test Stadium"},
                }
            ],
            "status": {"type": {"name": "STATUS_FINAL"}},
        }

        game = adapter._parse_game(event_data)

        assert game.id == "789"
        assert game.home_team.name == "Home Team"
        assert game.away_team.name == "Away Team"
        assert game.home_score == 3
        assert game.away_score == 2
        assert game.status == "final"
        assert game.quarter == "4"
        assert game.time_remaining == "0:00"
        assert game.venue == "Test Stadium"
