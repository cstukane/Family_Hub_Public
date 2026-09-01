from __future__ import annotations

from typing import Optional

from flask import jsonify, request

MAX_JSON_BYTES = 1_000_000  # 1 MB cap for API payloads


def _is_json_request() -> bool:
    """Return True when the request advertises a JSON body."""
    mimetype = (request.mimetype or "").lower()
    return mimetype == "application/json" or mimetype.endswith("+json")


def validate_request_json() -> Optional[tuple]:
    """
    Validate API request bodies for JSON endpoints.

    Returns a Flask response tuple when invalid, otherwise None.
    """
    if request.method in {"POST", "PUT", "PATCH"}:
        if request.content_length is not None and request.content_length > MAX_JSON_BYTES:
            return jsonify({"error": "Payload too large"}), 413

        if _is_json_request():
            if request.content_length in (None, 0):
                return None
            data = request.get_json(silent=True)
            if data is None:
                return jsonify({"error": "Invalid JSON"}), 400

    return None
