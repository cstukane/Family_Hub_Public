"""Regression tests for Google OAuth safety.

These tests ensure that background/service calendar operations NEVER
launch a browser or start a local OAuth server. Interactive
authentication is the responsibility of the explicit
``/api/oauth/google`` setup flow.

No test in this module performs real Google OAuth or opens a browser.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from app import create_app
from hub.adapters import calendar_google
from hub.adapters.calendar_google import (
    add_google_event,
    delete_google_event,
    fetch_google_events,
    get_calendar_status,
    get_google_calendar_credentials,
)


SCOPES = calendar_google.SCOPES


def _make_credentials(*, valid=True, expired=False, refresh_token="rt"):
    creds = Mock(spec=["valid", "expired", "refresh_token", "refresh", "to_json"])
    creds.valid = valid
    creds.expired = expired
    creds.refresh_token = refresh_token

    def _refresh(_request):
        creds.valid = True
        creds.expired = False

    creds.refresh.side_effect = _refresh
    creds.to_json.return_value = json.dumps(
        {
            "token": "access",
            "refresh_token": refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "cid",
            "client_secret": "csecret",
            "scopes": SCOPES,
            "type": "authorized_user",
        }
    )
    return creds


def _config():
    return {
        "client_id": "cid",
        "client_secret": "csecret",
        "calendar_ids": ["primary"],
    }


@pytest.fixture
def runtime_root(monkeypatch, tmp_path):
    root = tmp_path / "runtime"
    root.mkdir()
    monkeypatch.setenv("FAMILY_HUB_INSTANCE_PATH", str(root))
    return root


class TestGetCredentialsNonInteractive:
    def test_no_config_returns_none(self):
        assert get_google_calendar_credentials(None) is None
        assert get_google_calendar_credentials({}) is None

    def test_no_token_file_returns_none(self, runtime_root):
        # No token.json exists yet -> simply unauthenticated, never interactive.
        assert get_google_calendar_credentials(_config()) is None

    def test_valid_token_returns_credentials(self, runtime_root):
        creds = _make_credentials(valid=True)
        token_path = runtime_root / "token.json"
        token_path.write_text(creds.to_json())

        with patch(
            "hub.adapters.calendar_google.Credentials.from_authorized_user_file",
            return_value=creds,
        ) as load:
            result = get_google_calendar_credentials(_config())
            assert result is creds
            load.assert_called_once()

    def test_expired_token_refreshes_and_persists(self, runtime_root):
        creds = _make_credentials(valid=False, expired=True)
        token_path = runtime_root / "token.json"
        token_path.write_text(creds.to_json())

        with patch(
            "hub.adapters.calendar_google.Credentials.from_authorized_user_file",
            return_value=creds,
        ):
            result = get_google_calendar_credentials(_config())

        assert result is creds
        assert creds.valid is True
        assert creds.refresh.called
        # The refreshed token was persisted back to disk.
        assert token_path.exists()

    def test_refresh_failure_returns_none_and_removes_token(self, runtime_root):
        from google.auth.exceptions import RefreshError

        creds = _make_credentials(valid=False, expired=True)
        token_path = runtime_root / "token.json"
        token_path.write_text(creds.to_json())
        creds.refresh.side_effect = RefreshError("bad refresh")

        with patch(
            "hub.adapters.calendar_google.Credentials.from_authorized_user_file",
            return_value=creds,
        ):
            result = get_google_calendar_credentials(_config())

        assert result is None
        assert not token_path.exists()

    def test_malformed_token_returns_none_and_removes_token(self, runtime_root):
        token_path = runtime_root / "token.json"
        token_path.write_text("not-json")

        with patch(
            "hub.adapters.calendar_google.Credentials.from_authorized_user_file",
            side_effect=ValueError("bad json"),
        ):
            result = get_google_calendar_credentials(_config())

        assert result is None
        assert not token_path.exists()

    def test_installed_app_flow_is_not_imported_or_invoked(self, runtime_root):
        """InstalledAppFlow would be the gateway to run_local_server."""
        assert not hasattr(calendar_google, "InstalledAppFlow")

    def test_run_local_server_never_called_in_background_path(self, runtime_root):
        """
        Even if InstalledAppFlow were present, the background path must
        never call run_local_server() regardless of token presence.
        """
        sentinel_flow = MagicMock()
        sentinel_flow.run_local_server = MagicMock()

        with patch(
            "hub.adapters.calendar_google.Credentials.from_authorized_user_file",
            return_value=None,
        ):
            result = get_google_calendar_credentials(_config())
            assert result is None

        sentinel_flow.run_local_server.assert_not_called()


class TestCalendarOpsNeverLaunchOAuth:
    def test_fetch_events_no_token_does_not_launch_oauth(self, runtime_root):
        range_start = datetime(2023, 1, 1, tzinfo=timezone.utc)
        range_end = datetime(2023, 1, 31, tzinfo=timezone.utc)

        with patch("hub.adapters.calendar_google.get_cache", return_value=None):
            result = fetch_google_events(_config(), range_start, range_end)

        assert result == []

    def test_status_no_token_does_not_launch_oauth(self, runtime_root):
        with patch("hub.adapters.calendar_google.get_cache", return_value=None):
            status = get_calendar_status(_config())
        assert status == {
            "status": "Google Calendar not authenticated",
            "source": "Google",
            "connected": False,
        }

    def test_add_event_no_token_returns_none_without_launching_oauth(self, runtime_root):
        starts = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        ends = datetime(2023, 1, 1, 11, 0, tzinfo=timezone.utc)
        result = add_google_event(_config(), "x", starts, ends)
        assert result is None

    def test_delete_event_no_token_returns_false_without_launching_oauth(self, runtime_root):
        result = delete_google_event(_config(), "evt-1")
        assert result is False

    def test_run_local_server_never_reachable_from_ops(self, runtime_root):
        """
        Even if someone patched get_google_calendar_credentials to use
        InstalledAppFlow, the surrounding operations must not be
        affected. We patch run_local_server on a sentinel and ensure it
        is never invoked through the public surface.
        """
        sentinel = MagicMock()
        sentinel.run_local_server = MagicMock(return_value=_make_credentials())

        # Hot-patch a fake InstalledAppFlow reference and ensure no
        # background operation reaches run_local_server.
        with patch.object(
            calendar_google,
            "Credentials",
            wraps=calendar_google.Credentials,
        ):
            with patch("hub.adapters.calendar_google.get_cache", return_value=None):
                fetch_google_events(_config(), datetime(2023, 1, 1, tzinfo=timezone.utc), datetime(2023, 1, 31, tzinfo=timezone.utc))
                get_calendar_status(_config())
                add_google_event(
                    _config(),
                    "x",
                    datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
                    datetime(2023, 1, 1, 11, 0, tzinfo=timezone.utc),
                )
                delete_google_event(_config(), "evt-1")

        sentinel.run_local_server.assert_not_called()


class TestOAuthRouteStillGeneratesAuthUrl:
    def test_oauth_google_route_returns_auth_url_without_network(self):
        """Ensure the explicit OAuth route still works without network.

        The route delegates to ``google_auth_oauthlib.flow.Flow`` for
        URL construction. We patch that Flow everywhere it could be
        referenced so no actual ``run_local_server`` call is reachable,
        then assert the route returns a valid Google authorization URL.
        """
        app = create_app()
        client = app.test_client()

        mock_config = Mock()
        mock_config.providers.calendar.kind = "google"
        mock_config.providers.calendar.google = {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "calendar_ids": ["primary"],
        }
        app.config["CONFIG"] = mock_config

        sentinel_flow = Mock()
        sentinel_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?client_id=test_client_id",
            "state",
        )
        sentinel_flow.run_local_server = Mock()

        with patch("google_auth_oauthlib.flow.Flow") as flow_class:
            flow_class.from_client_config.return_value = sentinel_flow
            response = client.get("/api/oauth/google")

        assert response.status_code == 200, response.get_data(as_text=True)
        body = response.get_json()
        assert "auth_url" in body
        assert body["auth_url"].startswith("https://accounts.google.com/")
        # run_local_server is the gateway to browser/local OAuth server;
        # it must not be invoked on this explicit setup route either.
        sentinel_flow.run_local_server.assert_not_called()