"""TheSportsDB adapter for the Family Hub application."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests

from hub.models import Game, SportsData, Team
from hub.utils.http import RateLimitError, rate_limited_get


class TheSportsDBAdapter:
    """Adapter for TheSportsDB API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://www.thesportsdb.com/api/v1/json"
        self.logger = logging.getLogger(__name__)

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a request to TheSportsDB API."""
        if params is None:
            params = {}

        if self.api_key:
            params["api_key"] = self.api_key

        url = f"{self.base_url}/{endpoint}"

        try:
            response = rate_limited_get(url, params=params, timeout=10, service_name="thesportsdb")
            response.raise_for_status()
            return response.json()
        except RateLimitError as e:
            self.logger.error("TheSportsDB rate limited: %s", e)
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error making request to TheSportsDB: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"Error parsing JSON response from TheSportsDB: {e}")
            return None

    def _parse_team(self, team_data: Dict) -> Team:
        """Parse team data from API response."""
        return Team(
            id=team_data.get("idTeam", ""),
            name=team_data.get("strTeam", ""),
            abbreviation=team_data.get("strTeamShort", ""),
            logo_url=team_data.get("strTeamBadge"),
        )

    def _parse_game(self, event_data: Dict) -> Game:
        """Parse game data from API response."""
        # Parse home and away teams
        home_team = Team(
            id=event_data.get("idHomeTeam", ""),
            name=event_data.get("strHomeTeam", ""),
            abbreviation=event_data.get("strHomeTeamShort", ""),
            logo_url=event_data.get("strHomeTeamBadge"),
        )

        away_team = Team(
            id=event_data.get("idAwayTeam", ""),
            name=event_data.get("strAwayTeam", ""),
            abbreviation=event_data.get("strAwayTeamShort", ""),
            logo_url=event_data.get("strAwayTeamBadge"),
        )

        # Determine game status
        status = "scheduled"
        if event_data.get("strStatus") == "Finished":
            status = "final"
        elif event_data.get("strStatus") in ["In Progress", "Live"]:
            status = "in_progress"

        # Parse start time
        start_time = None
        date_str = event_data.get("dateEvent")
        time_str = event_data.get("strTime")

        if date_str:
            if time_str:
                datetime_str = f"{date_str} {time_str}"
                try:
                    start_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # Handle different time formats
                    try:
                        start_time = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        start_time = None
            else:
                try:
                    start_time = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    start_time = None

        # Parse scores
        home_score = 0
        away_score = 0
        try:
            home_score_str = event_data.get("intHomeScore", "0")
            away_score_str = event_data.get("intAwayScore", "0")
            home_score = int(home_score_str) if home_score_str else 0
            away_score = int(away_score_str) if away_score_str else 0
        except (ValueError, TypeError):
            pass

        # Parse quarter/period and time remaining
        quarter = event_data.get("strPeriod")
        time_remaining = event_data.get("strTime")

        return Game(
            id=event_data.get("idEvent", ""),
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            status=status,
            start_time=start_time,
            quarter=quarter,
            time_remaining=time_remaining,
            venue=event_data.get("strVenue"),
            broadcast=event_data.get("strTVStation"),
        )

    def get_sports_data(self, favorite_teams: Optional[List[str]] = None) -> SportsData:
        """Get sports data for today's games."""
        if favorite_teams is None:
            favorite_teams = []

        # Get today's events for all sports
        data = self._make_request("eventstoday.php")

        if not data:
            return SportsData(games=[], source="thesportsdb")

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

        return SportsData(games=games, source="thesportsdb")

    def get_team_info(self, team_name: str) -> Optional[Team]:
        """Get information about a specific team."""
        params = {"s": "NBA", "t": team_name}  # Example: NBA team lookup
        data = self._make_request("searchteams.php", params)

        if data and data.get("teams"):
            team_data = data["teams"][0]
            return self._parse_team(team_data)

        return None

    def get_leagues(self) -> Optional[List[Dict]]:
        """Get available leagues."""
        # For TheSportsDB, we can search for different sports
        # This is a simplified approach - in reality, we'd need to query for specific sports
        return [
            {"id": "nba", "name": "NBA"},
            {"id": "nfl", "name": "NFL"},
            {"id": "mlb", "name": "MLB"},
            {"id": "nhl", "name": "NHL"},
        ]
