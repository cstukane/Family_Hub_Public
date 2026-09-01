from flask import jsonify, request

from hub.utils.decorators import require_ip_whitelist

from . import api_bp

# Webhook API endpoints


@api_bp.route("/api/webhooks", methods=["GET"])
@require_ip_whitelist
def get_webhooks():
    """Get all webhooks."""
    from hub.services import webhook

    webhooks = webhook.get_all_webhooks()
    return jsonify([w.to_dict() for w in webhooks]), 200


@api_bp.route("/api/webhooks", methods=["POST"])
@require_ip_whitelist
def create_webhook():
    """Create a new webhook."""
    from hub.services import webhook

    data = request.get_json(silent=True) or {}

    name = data.get("name")
    url = data.get("url")
    event_types = data.get("event_types", ["weather_alert"])
    active = data.get("active", True)
    secret = data.get("secret")
    headers = data.get("headers", {})

    if not name or not url:
        return jsonify({"error": "Name and URL are required"}), 400

    created_webhook = webhook.create_webhook(name, url, event_types, active, secret, headers)
    if created_webhook:
        return jsonify(created_webhook.to_dict()), 201
    else:
        return jsonify({"error": "Failed to create webhook"}), 500


@api_bp.route("/api/webhooks/<int:webhook_id>", methods=["GET"])
@require_ip_whitelist
def get_webhook(webhook_id):
    """Get a specific webhook."""
    from hub.services import webhook

    webhook_obj = webhook.get_webhook(webhook_id)
    if webhook_obj:
        return jsonify(webhook_obj.to_dict()), 200
    else:
        return jsonify({"error": "Webhook not found"}), 404


@api_bp.route("/api/webhooks/<int:webhook_id>", methods=["PUT"])
@require_ip_whitelist
def update_webhook(webhook_id):
    """Update a webhook."""
    from hub.services import webhook

    data = request.get_json(silent=True) or {}

    success = webhook.update_webhook(
        webhook_id,
        name=data.get("name"),
        url=data.get("url"),
        event_types=data.get("event_types"),
        active=data.get("active"),
        secret=data.get("secret"),
        headers=data.get("headers"),
    )

    if success:
        updated_webhook = webhook.get_webhook(webhook_id)
        return jsonify(updated_webhook.to_dict()), 200
    else:
        return jsonify({"error": "Failed to update webhook"}), 500


@api_bp.route("/api/webhooks/<int:webhook_id>", methods=["DELETE"])
@require_ip_whitelist
def delete_webhook(webhook_id):
    """Delete a webhook."""
    from hub.services import webhook

    success = webhook.delete_webhook(webhook_id)
    if success:
        return jsonify({"status": "deleted"}), 200
    else:
        return jsonify({"error": "Failed to delete webhook"}), 500


@api_bp.route("/api/webhooks/<int:webhook_id>/test", methods=["POST"])
@require_ip_whitelist
def test_webhook(webhook_id):
    """Test a specific webhook."""
    from hub.services import webhook

    result = webhook.test_webhook_connection(webhook_id)
    return jsonify(result), 200


@api_bp.route("/api/webhooks/<int:webhook_id>/trigger", methods=["POST"])
@require_ip_whitelist
def trigger_webhook_endpoint(webhook_id):
    """Trigger a specific webhook with custom payload."""
    from hub.services import webhook

    data = request.get_json(silent=True) or {}
    payload = data.get("payload", {})

    success = webhook.trigger_webhook(webhook_id, payload)
    if success:
        return jsonify({"status": "triggered", "webhook_id": webhook_id}), 200
    else:
        return jsonify({"status": "failed", "webhook_id": webhook_id}), 500


@api_bp.route("/api/webhooks/trigger-all", methods=["POST"])
@require_ip_whitelist
def trigger_webhooks_for_event_endpoint():
    """Trigger webhooks for a specific event type."""
    from hub.services import webhook

    data = request.get_json(silent=True) or {}
    event_type = data.get("event_type", "weather_alert")
    payload = data.get("payload", {})

    async_dispatch = bool(data.get("async", data.get("async_dispatch", False)))
    triggered_count = webhook.trigger_webhooks_for_event(event_type, payload, async_dispatch=async_dispatch)
    return jsonify({"status": "triggered", "event_type": event_type, "triggered_count": triggered_count})


@api_bp.route("/api/webhooks/<int:webhook_id>/logs", methods=["GET"])
@require_ip_whitelist
def get_webhook_logs(webhook_id):
    """Get logs for a specific webhook."""
    from hub.services import webhook

    logs = webhook.get_webhook_logs(webhook_id)
    return jsonify([log.to_dict() for log in logs]), 200


@api_bp.route("/api/webhooks/logs", methods=["GET"])
@require_ip_whitelist
def get_all_webhook_logs():
    """Get all webhook logs."""
    from hub.services import webhook

    logs = webhook.get_all_webhook_logs()
    return jsonify([log.to_dict() for log in logs]), 200
