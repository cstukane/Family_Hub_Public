import logging
from unittest.mock import MagicMock, patch

import requests


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _configure_commute(app):
    commute = app.config["CONFIG"].commute
    commute.enabled = True
    commute.provider = "mapbox"
    commute.home_address = "origin-address"
    commute.work_address = "destination-address"
    commute.mapbox_token = "provider-credential"


def test_commute_request_uses_valid_mapbox_parameters_and_server_side_values(client, app):
    _configure_commute(app)
    responses = [
        _response({"features": [{"center": [-74.0, 40.0]}]}),
        _response({"features": [{"center": [-73.9, 40.1]}]}),
        _response({"routes": [{"duration": 1800, "duration_typical": 1500, "legs": []}]}),
    ]

    with patch("hub.routes.main.requests.get", side_effect=responses) as provider_get:
        response = client.get("/api/commute?window=morning")

    assert response.status_code == 200
    assert response.get_json()["eta_minutes"] == 30
    assert "origin-address" not in response.get_data(as_text=True)
    assert "provider-credential" not in response.get_data(as_text=True)

    first_geocode = provider_get.call_args_list[0]
    assert "origin-address" in first_geocode.args[0]
    assert first_geocode.kwargs == {
        "params": {"limit": 1, "access_token": "provider-credential"},
        "timeout": 10,
    }
    directions = provider_get.call_args_list[2]
    assert directions.kwargs == {
        "params": {
            "alternatives": "false",
            "annotations": "congestion,closure",
            "overview": "full",
            "access_token": "provider-credential",
        },
        "timeout": 10,
    }


def test_commute_detects_route_leg_incidents_and_annotation_closures(client, app):
    _configure_commute(app)

    for route in (
        {"duration": 1200, "legs": [{"incidents": [{"id": "event"}]}]},
        {"duration": 1200, "legs": [{"annotation": {"closure": [False, True]}}]},
    ):
        with patch(
            "hub.routes.main.requests.get",
            side_effect=[
                _response({"features": [{"center": [-74.0, 40.0]}]}),
                _response({"features": [{"center": [-73.9, 40.1]}]}),
                _response({"routes": [route]}),
            ],
        ):
            response = client.get("/api/commute")
        assert response.status_code == 200
        assert response.get_json()["has_incident"] is True


def test_commute_failure_logging_suppresses_sensitive_request_details(client, app, caplog):
    _configure_commute(app)
    sensitive_url = (
        "https://api.mapbox.com/geocoding/v5/mapbox.places/"
        "origin-address.json?access_token=provider-credential"
    )

    with (
        patch(
            "hub.routes.main.requests.get",
            side_effect=requests.RequestException(f"request failed: {sensitive_url}"),
        ),
        caplog.at_level(logging.WARNING),
    ):
        response = client.get("/api/commute")

    assert response.status_code == 502
    log_output = caplog.text
    assert "Commute provider request failed" in log_output
    assert "origin-address" not in log_output
    assert "provider-credential" not in log_output
    assert "api.mapbox.com" not in log_output


def test_disabled_commute_does_not_contact_provider(client, app):
    app.config["CONFIG"].commute.enabled = False
    with patch("hub.routes.main.requests.get") as provider_get:
        response = client.get("/api/commute")
    assert response.status_code == 404
    provider_get.assert_not_called()
