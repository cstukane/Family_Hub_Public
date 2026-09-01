#!/usr/bin/env python3
"""
Minimal Flask app for the Family Hub UI that serves static files and basic routes.
This is a simplified server for the media child windows feature that serves
the hub UI and media control endpoints.
"""

import os
import secrets
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, make_response, request, send_from_directory

from hub.utils.auth import AuthError, generate_media_launcher_token, verify_media_launcher_token
from hub.utils.logging_config import configure_logging

app = Flask(__name__)
configure_logging(app)

# Configure secret key for sessions/cookies
hub_secret = os.environ.get("SECRET_KEY")
if not hub_secret:
    hub_secret = secrets.token_urlsafe(48)
    os.environ["SECRET_KEY"] = hub_secret
    app.logger.warning("SECRET_KEY is not set; generated a temporary key for this session.")
app.secret_key = hub_secret

HUB_APP_AUTH_ENABLED = str(os.environ.get("HUB_APP_AUTH_ENABLED", "true")).strip().lower() in {"1", "true", "yes", "on"}


def _env_truthy(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _media_token_ttl() -> int:
    return int(os.environ.get("MEDIA_LAUNCHER_TOKEN_TTL", "300"))


def _issue_media_token() -> str:
    return generate_media_launcher_token(ttl_seconds=_media_token_ttl())


@app.before_request
def enforce_hub_app_auth():
    if not HUB_APP_AUTH_ENABLED:
        return None
    if request.endpoint in {"health", "static_files"}:
        return None
    if request.endpoint == "index":
        return None

    token = request.cookies.get("hub_app_token")
    if not token:
        return jsonify({"ok": False, "err": "unauthorized"}), 401
    try:
        verify_media_launcher_token(token)
    except AuthError:
        return jsonify({"ok": False, "err": "unauthorized"}), 401


# Serve static files from hub_ui folder
@app.route("/")
def index():
    """Serve the main hub UI."""
    index_path = Path("hub_ui") / "index.html"
    token = _issue_media_token()
    html = index_path.read_text(encoding="utf-8")
    html = html.replace("__MEDIA_LAUNCHER_TOKEN__", token)
    response = make_response(html)
    secure_cookie = (
        _env_truthy(os.environ.get("HUB_APP_SECURE_COOKIE"))
        if os.environ.get("HUB_APP_SECURE_COOKIE") is not None
        else request.is_secure
    )
    response.set_cookie(
        "hub_app_token",
        token,
        httponly=True,
        samesite="Lax",
        secure=secure_cookie,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/<path:path>")
def static_files(path):
    """Serve static files from hub_ui folder."""
    return send_from_directory("hub_ui", path)


@app.route("/media_control")
def media_control():
    """Serve the media controller overlay (for child windows)."""
    token = _issue_media_token()
    controller_html = """
<!doctype html>
<html>
<head>
  <style>
    body { margin:0; background:transparent; }
    #ctrl { position: fixed; left:8px; top:8px; z-index:9999; }
    button { font-size:18px; padding:8px 12px; border-radius:6px;
             background: rgba(0,0,0,0.7); color: white;
             border: 1px solid white; cursor: pointer; }
    button:hover { background: rgba(50,50,50,0.9); }
  </style>
</head>
<body>
  <div id="ctrl">
    <button id="closeBtn">⤺ Home</button>
  </div>
  <script>
    document.getElementById('closeBtn').addEventListener('click', async () => {
      try {
        await fetch('http://127.0.0.1:7666/v1/close_media', {
          method: 'POST',
          headers: {
            'Authorization': 'Bearer __MEDIA_LAUNCHER_TOKEN__'
          }
        });
        // Optionally close this controller window (if launched separately)
        try { window.close(); } catch(e){}
      } catch(err) {
        console.error('Failed to close media:', err);
      }
    });
  </script>
</body>
</html>
    """
    return controller_html.replace("__MEDIA_LAUNCHER_TOKEN__", token)


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "hub_app"})


if __name__ == "__main__":
    # Run on 127.0.0.1:5000 as specified
    app.run(host="127.0.0.1", port=5000, debug=False)
