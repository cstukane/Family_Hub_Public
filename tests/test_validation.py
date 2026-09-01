from flask import Flask, jsonify

from hub.utils.validation import MAX_JSON_BYTES, validate_request_json


def _create_app():
    app = Flask(__name__)

    @app.before_request
    def _validate_json():
        result = validate_request_json()
        if result:
            return result
        return None

    @app.route("/ping", methods=["POST"])
    def ping():
        return jsonify({"ok": True})

    return app


def test_invalid_json_returns_400():
    app = _create_app()
    client = app.test_client()
    response = client.post("/ping", data="{invalid", content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid JSON"


def test_payload_too_large_returns_413():
    app = _create_app()
    client = app.test_client()
    payload = "a" * (MAX_JSON_BYTES + 1)
    response = client.post("/ping", data=payload, content_type="application/json")
    assert response.status_code == 413
    assert response.get_json()["error"] == "Payload too large"


def test_valid_json_passes_through():
    app = _create_app()
    client = app.test_client()
    response = client.post("/ping", json={"value": 123})
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
