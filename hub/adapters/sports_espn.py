"""ESPN adapter for the Family Hub application."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests

from hub.models import Game, SportsData, Team
from hub.utils.http import RateLimitError, rate_limited_get


class ESPNAdapter:
    """Adapter for ESPN API (unofficial)."""

    def __init__(self):
        self.base_url = "http://site.api.espn.com/apis/site/v2/sports"
        self.logger = logging.getLogger(__name__)

    def _make_request(self, endpoint: str) -> Optional[Dict]:
        """Make a request to ESPN API."""
        url = f"{self.base_url}/{endpoint}"

        try:
            response = rate_limited_get(url, timeout=10, service_name="espn")
            response.raise_for_status()
            return response.json()
        except RateLimitError as e:
            self.logger.error("ESPN API rate limited: %s", e)
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error making request to ESPN: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"Error parsing JSON response from ESPN: {e}")
            return None

    def _parse_team(self, team_data: Dict) -> Team:
        """Parse team data from API response."""
        return Team(
            id=team_data.get("id", ""),
            name=team_data.get("displayName", ""),
            abbreviation=team_data.get("abbreviation", ""),
            logo_url=team_data.get("logo"),  # This might be None for some teams
        )

    def _parse_game(self, event_data: Dict) -> Game:
        """Parse game data from API response."""
        # Extract home and away teams
        home_team_data = None
        away_team_data = None

        for competitor in event_data.get("competitions", [{}])[0].get("competitors", []):
            if competitor.get("homeAway") == "home":
                home_team_data = competitor.get("team", {})
            elif competitor.get("homeAway") == "away":
                away_team_data = competitor.get("team", {})

        # Create team objects
        home_team = self._parse_team(home_team_data) if home_team_data else Team(name="Home Team")
        away_team = self._parse_team(away_team_data) if away_team_data else Team(name="Away Team")

        # Get competition data
        competition = event_data.get("competitions", [{}])[0] if event_data.get("competitions") else {}

        # Determine game status
        status = event_data.get("status", {}).get("type", {}).get("name", "STATUS_SCHEDULED").lower()
        if "completed" in status or "final" in status:
            status = "final"
        elif "in" in status or "live" in status or "progress" in status:
            status = "in_progress"
        else:
            status = "scheduled"

        # Parse start time
        start_time = None
        date_str = event_data.get("date")
        if date_str:
            try:
                start_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                self.logger.warning(f"Could not parse date: {date_str}")

        # Parse scores
        home_score = 0
        away_score = 0
        if competition.get("competitors"):
            for competitor in competition["competitors"]:
                if competitor.get("homeAway") == "home":
                    home_score = int(competitor.get("score", 0))
                elif competitor.get("homeAway") == "away":
                    away_score = int(competitor.get("score", 0))

        # Parse quarter/period and time remaining
        quarter = competition.get("status", {}).get("period", "")
        time_remaining = competition.get("status", {}).get("displayClock", "")

        return Game(
            id=event_data.get("id", ""),
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            status=status,
            start_time=start_time,
            quarter=str(quarter) if quarter else None,
            time_remaining=time_remaining if time_remaining else None,
            venue=competition.get("venue", {}).get("fullName"),
            broadcast=None,  # ESPN doesn't typically provide this via the public API
        )

    def get_sports_data(self, favorite_teams: Optional[List[str]] = None) -> SportsData:
        """Get sports data from ESPN (NBA as an example)."""
        if favorite_teams is None:
            favorite_teams = []

        # Example: Get NBA games for today
        # Note: The actual ESPN API structure has different endpoints for different sports
        # This is a simplified implementation for demonstration
        endpoint = "basketball/nba/scoreboard"
        data = self._make_request(endpoint)

        if not data:
            # Try alternative endpoints for other sports
            data = self._make_request("football/nfl/scoreboard")
            if not data:
                return SportsData(games=[], source="espn")

        events = data.get("events", [])
        games = []

        for event_data in events:
            game = self._parse_game(event_data)

            # Filter by favorite teams if provided
            if favorite_teams:
                home_team_name = game.home_team.name.lower()
                away_team_name = game.away_team.name.lower()

                # Check if any favorite team name is in the home or away team names
                is_favorite = any(
                    fav_team.lower() in home_team_name or fav_team.lower() in away_team_name
                    for fav_team in favorite_teams
                )

                if not is_favorite:
                    continue

            games.append(game)

        return SportsData(games=games, source="espn")

    def get_team_info(self, team_name: str) -> Optional[Team]:
        """Get information about a specific team."""
        # This would require a more complex implementation to search for teams
        # For now, we return None to indicate this functionality is not fully implemented
        return None

    def get_leagues(self) -> Optional[List[Dict]]:
        """Get available leagues."""
        return [
            {"id": "nba", "name": "NBA"},
            {"id": "nfl", "name": "NFL"},
            {"id": "mlb", "name": "MLB"},
            {"id": "nhl", "name": "NHL"},
        ]
