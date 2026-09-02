from flask import Blueprint

# Create blueprints
main_bp = Blueprint("main", __name__)
api_bp = Blueprint("api", __name__)

from . import api, api_admin, api_media_admin, main  # noqa: F401
