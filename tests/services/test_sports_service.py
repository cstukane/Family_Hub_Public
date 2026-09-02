"""Tests for sports service."""

from unittest.mock import Mock, patch

import pytest

from hub.models import Game, SportsData, Team
from hub.services import sports


class TestSportsService:
    """Test the sports service functions."""

    def test_get_sports_data_with_no_favorite_teams(self, app):
        """Test getting sports data when no favorite teams are specified."""
        with app.app_context():
            with patch("hub.services.sports._get_adapter") as mock_adapter:
                mock_adapter.return_value = Mock()
                mock_adapter.return_value.get_sports_data.return_value = SportsData(games=[], source="test")

                result = sports.get_sports_data(favorite_teams=[])

                # Verify that get_sports_data was called with None (for main stories)
                mock_adapter.return_value.get_sports_data.assert_called_once_with(None)
                assert result.source == "test"

    def test_get_sports_data_with_favorite_teams(self, app):
        """Test getting sports data with favorite teams."""
        with app.app_context():
            with patch("hub.services.sports._get_adapter") as mock_adapter:
                # Mock the adapter to return different data for main stories and favorite teams
                def mock_get_sports_data(teams_filter):
                    if teams_filter is None:
                        # Main stories
                        main_team = Team(name="Main Team 1", abbreviation="MT1")
                        main_game = Game(
                            id="main_game_1",
                            home_team=main_team,
                            away_team=Team(name="Main Team 2", abbreviation="MT2"),
                            status="scheduled",
                        )
                        return SportsData(games=[main_game], source="main")
                    else:
                        # Favorite team games
                        fav_team = Team(name="Favorite Team 1", abbreviation="FT1")
                        fav_game = Game(
                            id="fav_game_1",
                            home_team=fav_team,
                            away_team=Team(name="Favorite Team 2", abbreviation="FT2"),
                            status="in_progress",
                        )
                        return SportsData(games=[fav_game], source="favorites")

                mock_adapter.return_value.get_sports_data.side_effect = mock_get_sports_data

                result = sports.get_sports_data(favorite_teams=["fav_team_1"])

                # Verify that both main and favorite team data were fetched
                assert len(mock_adapter.return_value.get_sports_data.call_args_list) >= 2
                # First call should be for main stories (None filter)
                # Second call should be for favorite teams
                assert len(result.games) == 2  # Should include both main and favorite games

    def test_refresh_sports_data(self, app):
        """Test refreshing sports data."""
        with app.app_context():
            with (
                patch("hub.services.sports._get_adapter") as mock_get_adapter,
                patch("hub.cache.delete_cache") as mock_delete,
                patch("hub.services.sports.set_cache") as mock_set,
            ):
                mock_adapter = Mock()
                mock_adapter.get_sports_data.return_value = SportsData(games=[], source="test")
                mock_get_adapter.return_value = mock_adapter

                result = sports.refresh_sports_data()

                # Should return True for successful refresh
                assert result is True
                mock_delete.assert_called()  # Should delete cache
                mock_set.assert_called()  # Should set new cache

    def test_get_team_info(self, app):
        """Test getting team info."""
        with app.app_context():
            with patch("hub.services.sports._get_adapter") as mock_adapter:
                mock_team = Team(name="Test Team", abbreviation="TT")
                mock_adapter.return_value.get_team_info.return_value = mock_team

                result = sports.get_team_info("test_team")

                assert result["name"] == "Test Team"
                assert result["abbreviation"] == "TT"
                mock_adapter.return_value.get_team_info.assert_called_once_with("test_team")

    def test_get_available_leagues(self, app):
        """Test getting available leagues."""
        mock_leagues = [{"id": "nba", "name": "NBA"}, {"id": "nfl", "name": "NFL"}]

        with app.app_context():
            with patch("hub.services.sports._get_adapter") as mock_adapter:
                mock_adapter.return_value.get_leagues.return_value = mock_leagues

                result = sports.get_available_leagues()

                assert result == mock_leagues
                mock_adapter.return_value.get_leagues.assert_called_once()

    def test_update_favorite_teams(self, app):
        """Test updating favorite teams."""
        # Create a temporary config file for testing
        import os
        import tempfile

        import yaml

        test_config = {"providers": {"sports": {"favorite_teams": ["old_team"]}}}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            yaml.dump(test_config, f)
            temp_config_path = f.name

        try:
            # Use the app context and update the app's config to use our temp config file
            with app.app_context():
                app.config["CONFIG_PATH"] = temp_config_path

                result = sports.update_favorite_teams(["new_team1", "new_team2"])

                assert result is True

                # Verify the file was updated
                with open(temp_config_path, "r") as f:
                    updated_config = yaml.safe_load(f)

                assert updated_config["providers"]["sports"]["favorite_teams"] == ["new_team1", "new_team2"]
        finally:
            # Clean up temp file
            os.unlink(temp_config_path)
