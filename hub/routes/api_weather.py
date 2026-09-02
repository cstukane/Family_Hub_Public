from flask import jsonify, request

from hub.utils.decorators import require_admin_rate_limit, require_default_rate_limit

from . import api_bp

# Weather Alert API endpoints


@api_bp.route("/api/weather-alerts", methods=["GET"])
@require_default_rate_limit
def get_weather_alerts():
    """Get current weather alerts."""
    from hub.services import weather_alert

    alerts = weather_alert.get_active_weather_alerts()
    return jsonify({"alerts": alerts}), 200


@api_bp.route("/api/weather-alerts/history", methods=["GET"])
@require_default_rate_limit
def get_weather_alert_history():
    """Get weather alert history."""
    from hub.services import weather_alert

    hours = int(request.args.get("hours", 24))
    if hours > 168:  # Limit to 1 week max
        hours = 168

    alerts = weather_alert.get_weather_alert_history(hours)
    return jsonify({"alerts": alerts}), 200


@api_bp.route("/api/weather-alerts/check", methods=["POST"])
@require_admin_rate_limit
def check_weather_alerts():
    """Manually check for weather alerts."""
    from hub.services import weather_alert

    result = weather_alert.process_weather_alerts()
    return jsonify(result), 200


@api_bp.route("/api/weather-alerts/severity", methods=["GET"])
@require_default_rate_limit
def get_weather_severity():
    """Get current weather severity level."""
    from hub.services import weather_alert

    is_severe = weather_alert.is_weather_severe()
    current_weather = weather_alert.get_current_weather_data()

    return jsonify({"is_severe": is_severe, "current_weather": current_weather}), 200
