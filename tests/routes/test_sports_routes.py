"""Tests for sports API routes."""

import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest


class TestSportsAPIRoutes:
    """Test the sports API routes."""

    def test_get_sports_data(self, client):
        """Test getting sports data."""
        with patch("hub.services.sports.get_sports_data") as mock_get_sports:
            mock_sports_data = Mock()
            mock_sports_data.to_dict.return_value = {
                "games": [],
                "last_updated": "2023-10-01T12:00:00+00:00",
                "source": "test",
            }
            mock_get_sports.return_value = mock_sports_data

            response = client.get("/api/sports")

            assert response.status_code == 200
            data = response.get_json()
            assert data["source"] == "test"

    def test_refresh_sports_data(self, client):
        """Test refreshing sports data."""
        from hub.models import Game, SportsData, Team

        with (
            patch("hub.services.sports.refresh_sports_data") as mock_refresh,
            patch("hub.services.sports.get_sports_data") as mock_get_sports,
        ):
            mock_refresh.return_value = True
            # Create a proper SportsData instance for the template
            mock_sports_data = SportsData(games=[])
            mock_get_sports.return_value = mock_sports_data

            response = client.post("/api/sports/refresh")

            assert response.status_code == 200
            # Response should contain rendered HTML for the ticker partial

    def test_get_sports_last_updated(self, client):
        """Test getting sports last updated time."""
        with patch("hub.services.sports.get_sports_data") as mock_get_sports:
            mock_sports_data = Mock()
            mock_sports_data.last_updated = datetime.now(timezone.utc)
            mock_get_sports.return_value = mock_sports_data

            response = client.get("/api/sports/last-updated")

            assert response.status_code == 200
            response_text = response.get_data(as_text=True)
            assert "Updated" in response_text

    def test_get_favorite_teams(self, client):
        """Test getting favorite teams."""
        # The favorite teams should be part of the config which is set up in conftest.py
        # Add sports config to the app
        from flask import current_app

        response = client.get("/api/sports/favorite_teams")

        assert response.status_code == 200
        data = response.get_json()
        # It should return an array (empty if not configured)
        assert "favorite_teams" in data

    def test_manage_favorite_teams_get(self, client):
        """Test getting favorite teams via manage endpoint."""
        response = client.get("/api/sports/favorite_teams")

        assert response.status_code == 200
        data = response.get_json()
        assert "favorite_teams" in data

    def test_manage_favorite_teams_post(self, client):
        """Test updating favorite teams via manage endpoint."""
        from hub.models import Game, SportsData, Team

        with (
            patch("hub.services.sports.update_favorite_teams") as mock_update,
            patch("hub.services.sports.get_sports_data") as mock_get_sports,
        ):
            mock_update.return_value = True
            # Create a proper SportsData instance for the template
            mock_sports_data = SportsData(games=[])
            mock_get_sports.return_value = mock_sports_data

            response = client.post(
                "/api/sports/favorite_teams",
                data=json.dumps({"favorite_teams": ["new_team1", "new_team2"]}),
                content_type="application/json",
            )

            assert response.status_code == 200
            # Response should contain rendered HTML for the ticker partial

    def test_add_favorite_team(self, client):
        """Test adding a favorite team."""
        with patch("hub.services.sports.update_favorite_teams") as mock_update:
            mock_update.return_value = True

            # Test JSON request
            response = client.post(
                "/api/sports/favorite_teams/add",
                data=json.dumps({"team_name": "new_team"}),
                content_type="application/json",
            )

            assert response.status_code == 200
            # Response should contain rendered HTML for the manage teams partial

    def test_get_sports_partial(self, client):
        """Test getting sports ticker partial."""
        from hub.models import Game, SportsData, Team

        with patch("hub.services.sports.get_sports_data") as mock_get_sports:
            mock_sports_data = SportsData(games=[])
            mock_get_sports.return_value = mock_sports_data

            response = client.get("/partials/sports")

            assert response.status_code == 200
            # Response should contain rendered HTML for the ticker partial
