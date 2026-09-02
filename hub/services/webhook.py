"""Webhook service for triggering external notifications."""

import hashlib
import hmac
import json
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from flask import current_app, has_app_context

from hub.db import get_db
from hub.utils.http import RateLimitError, rate_limited_post, rate_limited_request

logger = logging.getLogger(__name__)

_MAX_WEBHOOK_WORKERS = max(2, min(8, os.cpu_count() or 2))
_WEBHOOK_EXECUTOR = ThreadPoolExecutor(max_workers=_MAX_WEBHOOK_WORKERS)
_DEFAULT_RETRY_CONFIG = {
    "max_attempts": 3,
    "base_delay": 1.0,
    "max_delay": 8.0,
    "jitter": 0.2,
    "retry_statuses": {408, 429, 500, 502, 503, 504},
}


class Webhook:
    """Webhook model representing a configured webhook endpoint."""

    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        url: str = "",
        event_types: List[str] = None,
        active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.id = id
        self.name = name
        self.url = url
        self.event_types = event_types or ["weather_alert"]
        self.active = active
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.secret = secret
        self.headers = headers or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert webhook to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "event_types": self.event_types,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "headers": self.headers,
        }


class WebhookLog:
    """Webhook log model for tracking webhook executions."""

    def __init__(
        self,
        id: Optional[int] = None,
        webhook_id: int = 0,
        payload: Optional[Dict[str, Any]] = None,
        status: str = "",
        response: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.id = id
        self.webhook_id = webhook_id
        self.payload = payload or {}
        self.status = status  # success, error, timeout
        self.response = response
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert webhook log to dictionary."""
        return {
            "id": self.id,
            "webhook_id": self.webhook_id,
            "payload": self.payload,
            "status": self.status,
            "response": self.response,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


def create_webhook(
    name: str,
    url: str,
    event_types: List[str],
    active: bool = True,
    secret: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[Webhook]:
    """Create a new webhook configuration."""
    db = get_db()

    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL")
    except Exception:
        current_app.logger.error(f"Invalid webhook URL: {url}")
        return None

    query = """
        INSERT INTO webhooks (name, url, event_types, active, secret, headers)
        VALUES (?, ?, ?, ?, ?, ?)
        RETURNING id, name, url, event_types, active, created_at, updated_at, secret, headers
    """

    try:
        # Convert event_types to JSON string
        event_types_json = json.dumps(event_types)
        headers_json = json.dumps(headers) if headers else json.dumps({})

        row = db.execute(query, (name, url, event_types_json, active, secret, headers_json)).fetchone()
        db.commit()

        if row:
            # Parse event_types back from JSON
            event_types = json.loads(row["event_types"])
            headers = json.loads(row["headers"])

            return Webhook(
                id=row["id"],
                name=row["name"],
                url=row["url"],
                event_types=event_types,
                active=bool(row["active"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                secret=row["secret"],
                headers=headers,
            )
    except Exception as e:
        current_app.logger.error(f"Error creating webhook: {e}")
        db.rollback()

    return None


def get_webhook(webhook_id: int) -> Optional[Webhook]:
    """Get a webhook by ID."""
    db = get_db()

    query = "SELECT * FROM webhooks WHERE id = ?"
    row = db.execute(query, (webhook_id,)).fetchone()

    if row:
        event_types = json.loads(row["event_types"])
        headers = json.loads(row["headers"]) if row["headers"] else {}

        return Webhook(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            event_types=event_types,
            active=bool(row["active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            secret=row["secret"],
            headers=headers,
        )

    return None


def get_all_webhooks() -> List[Webhook]:
    """Get all webhooks."""
    db = get_db()

    query = "SELECT * FROM webhooks ORDER BY created_at DESC"
    rows = db.execute(query).fetchall()

    webhooks = []
    for row in rows:
        event_types = json.loads(row["event_types"])
        headers = json.loads(row["headers"]) if row["headers"] else {}

        webhooks.append(
            Webhook(
                id=row["id"],
                name=row["name"],
                url=row["url"],
                event_types=event_types,
                active=bool(row["active"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                secret=row["secret"],
                headers=headers,
            )
        )

    return webhooks


def update_webhook(
    webhook_id: int,
    name: Optional[str] = None,
    url: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    active: Optional[bool] = None,
    secret: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> bool:
    """Update a webhook configuration."""
    db = get_db()

    # Get current webhook to apply updates
    current_webhook = get_webhook(webhook_id)
    if not current_webhook:
        return False

    # Apply updates
    update_fields = []
    params = []

    if name is not None:
        update_fields.append("name = ?")
        params.append(name)
    if url is not None:
        # Validate URL
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL")
        except Exception:
            current_app.logger.error(f"Invalid webhook URL: {url}")
            return False
        update_fields.append("url = ?")
        params.append(url)
    if event_types is not None:
        update_fields.append("event_types = ?")
        params.append(json.dumps(event_types))
    if active is not None:
        update_fields.append("active = ?")
        params.append(active)
    if secret is not None:
        update_fields.append("secret = ?")
        params.append(secret)
    if headers is not None:
        update_fields.append("headers = ?")
        params.append(json.dumps(headers))

    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(webhook_id)

    query = f"UPDATE webhooks SET {', '.join(update_fields)} WHERE id = ?"  # nosec B608

    try:
        db.execute(query, params)
        db.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error updating webhook: {e}")
        db.rollback()
        return False


def delete_webhook(webhook_id: int) -> bool:
    """Delete a webhook."""
    db = get_db()

    query = "DELETE FROM webhooks WHERE id = ?"

    try:
        db.execute(query, (webhook_id,))
        db.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error deleting webhook: {e}")
        db.rollback()
        return False


def trigger_webhook(webhook_id: int, payload: Dict[str, Any]) -> bool:
    """Trigger a specific webhook with the provided payload."""
    webhook = get_webhook(webhook_id)
    if not webhook or not webhook.active:
        return False

    return _send_webhook_request(webhook, payload)


def trigger_webhooks_for_event(event_type: str, payload: Dict[str, Any], async_dispatch: bool = False) -> int:
    """Trigger all active webhooks configured for a specific event type."""
    all_webhooks = get_all_webhooks()
    triggered_count = 0

    for webhook in all_webhooks:
        if webhook.active and event_type in webhook.event_types:
            if async_dispatch:
                _dispatch_webhook_async(webhook, payload)
                triggered_count += 1
            else:
                success = _send_webhook_request(webhook, payload)
                if success:
                    triggered_count += 1

    return triggered_count


def _dispatch_webhook_async(webhook: Webhook, payload: Dict[str, Any]) -> None:
    if not has_app_context():
        _send_webhook_request(webhook, payload)
        return

    app = current_app._get_current_object()
    _WEBHOOK_EXECUTOR.submit(_send_webhook_request_with_context, app, webhook, payload)


def _send_webhook_request_with_context(app, webhook: Webhook, payload: Dict[str, Any]) -> None:
    with app.app_context():
        _send_webhook_request(webhook, payload)


def _send_webhook_request(webhook: Webhook, payload: Dict[str, Any]) -> bool:
    """Send HTTP request to a webhook URL with payload."""
    log = current_app.logger if has_app_context() else logger
    webhook_payload = _build_webhook_payload(payload)
    headers = _build_webhook_headers(webhook, webhook_payload)
    retry_config = _get_webhook_retry_config()
    max_attempts = retry_config["max_attempts"]
    retry_statuses = retry_config["retry_statuses"]
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = rate_limited_post(
                webhook.url,
                json=webhook_payload,
                headers=headers,
                timeout=30,
                service_name="webhook",
            )

            if 200 <= response.status_code < 300:
                log_webhook_execution(
                    webhook.id,
                    webhook_payload,
                    "success",
                    response.text if response.text else str(response.status_code),
                )
                log.info("Webhook %s triggered successfully", webhook.name)
                return True

            last_error = f"status {response.status_code}"
            if response.status_code in retry_statuses and attempt < max_attempts:
                retry_after = response.headers.get("Retry-After")
                _sleep_before_retry(webhook, attempt, retry_config, retry_after)
                continue

            log_webhook_execution(
                webhook.id, webhook_payload, "error", response.text if response.text else str(response.status_code)
            )
            log.warning("Webhook %s returned status %s", webhook.name, response.status_code)
            return False
        except RateLimitError as e:
            last_error = str(e)
            if attempt < max_attempts:
                _sleep_before_retry(webhook, attempt, retry_config)
                continue
            log.error("Webhook %s rate limited: %s", webhook.name, e)
            log_webhook_execution(webhook.id, webhook_payload, "error", str(e))
            return False
        except requests.exceptions.Timeout:
            last_error = "Request timed out"
            if attempt < max_attempts:
                _sleep_before_retry(webhook, attempt, retry_config)
                continue
            log.error("Webhook %s request timed out", webhook.name)
            log_webhook_execution(webhook.id, webhook_payload, "timeout", "Request timed out")
            return False
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            if attempt < max_attempts:
                _sleep_before_retry(webhook, attempt, retry_config)
                continue
            log.error("Webhook %s request failed: %s", webhook.name, e)
            log_webhook_execution(webhook.id, webhook_payload, "error", str(e))
            return False
        except Exception as e:
            last_error = str(e)
            if attempt < max_attempts:
                _sleep_before_retry(webhook, attempt, retry_config)
                continue
            log.error("Webhook %s error: %s", webhook.name, e)
            log_webhook_execution(webhook.id, webhook_payload, "error", str(e))
            return False

    log_webhook_execution(webhook.id, webhook_payload, "error", last_error or "unknown error")
    return False


def _build_webhook_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    config = current_app.config.get("CONFIG")
    version = getattr(config, "version", "unknown") if config else "unknown"
    return {
        "event_type": payload.get("event_type", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "data": payload.get("data", {}),
        "kitchen_hub": {"version": version, "instance": current_app.config.get("CONFIG_PATH", "default")},
    }


def _build_webhook_headers(webhook: Webhook, webhook_payload: Dict[str, Any]) -> Dict[str, str]:
    headers = {"Content-Type": "application/json", "User-Agent": "KitchenHub-Webhook-Client/1.0"}

    headers.update(webhook.headers)

    if webhook.secret:
        signature = _generate_signature(webhook.secret, webhook_payload)
        headers["X-Webhook-Signature"] = signature

    return headers


def _get_webhook_retry_config() -> Dict[str, Any]:
    config = current_app.config.get("CONFIG") if has_app_context() else None
    retry_config = getattr(config, "webhook_retry", None) if config else None

    if isinstance(retry_config, dict):
        merged = dict(_DEFAULT_RETRY_CONFIG)
        merged.update({k: v for k, v in retry_config.items() if v is not None})
        retry_statuses = merged.get("retry_statuses", _DEFAULT_RETRY_CONFIG["retry_statuses"])
        merged["retry_statuses"] = set(retry_statuses)
        return merged

    if retry_config is not None:
        merged = dict(_DEFAULT_RETRY_CONFIG)
        for key in _DEFAULT_RETRY_CONFIG.keys():
            value = getattr(retry_config, key, None)
            if value is not None:
                merged[key] = value
        merged["retry_statuses"] = set(merged.get("retry_statuses", _DEFAULT_RETRY_CONFIG["retry_statuses"]))
        return merged

    return dict(_DEFAULT_RETRY_CONFIG)


def _sleep_before_retry(
    webhook: Webhook, attempt: int, retry_config: Dict[str, Any], retry_after: Optional[str] = None
) -> None:
    delay = _calculate_retry_delay(attempt, retry_config, retry_after)
    if delay <= 0:
        return
    current_app.logger.warning(
        f"Webhook {webhook.name} retrying after {delay:.1f}s (attempt {attempt + 1}/{retry_config['max_attempts']})"
    )
    time.sleep(delay)


def _calculate_retry_delay(attempt: int, retry_config: Dict[str, Any], retry_after: Optional[str] = None) -> float:
    if retry_after:
        try:
            return min(float(retry_after), float(retry_config["max_delay"]))
        except (TypeError, ValueError):
            pass

    base_delay = float(retry_config["base_delay"])
    max_delay = float(retry_config["max_delay"])
    jitter = float(retry_config["jitter"])
    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
    if jitter > 0:
        delay *= 1 + random.uniform(-jitter, jitter)  # nosec B311
    return max(0.0, delay)


def _generate_signature(secret: str, payload: Dict[str, Any]) -> str:
    """Generate HMAC signature for webhook payload."""
    try:
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        signature = hmac.new(secret.encode("utf-8"), payload_json.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"sha256={signature}"
    except Exception as e:
        current_app.logger.error(f"Error generating webhook signature: {e}")
        return ""


def log_webhook_execution(
    webhook_id: int, payload: Dict[str, Any], status: str, response: Optional[str] = None
) -> bool:
    """Log a webhook execution to the database."""
    db = get_db()

    query = """
        INSERT INTO webhook_logs (webhook_id, payload, status, response)
        VALUES (?, ?, ?, ?)
    """

    try:
        payload_json = json.dumps(payload)
        db.execute(query, (webhook_id, payload_json, status, response))
        db.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error logging webhook execution: {e}")
        return False


def get_webhook_logs(webhook_id: int, limit: int = 50) -> List[WebhookLog]:
    """Get logs for a specific webhook."""
    db = get_db()

    query = """
        SELECT * FROM webhook_logs
        WHERE webhook_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    rows = db.execute(query, (webhook_id, limit)).fetchall()

    logs = []
    for row in rows:
        payload = json.loads(row["payload"]) if row["payload"] else {}
        logs.append(
            WebhookLog(
                id=row["id"],
                webhook_id=row["webhook_id"],
                payload=payload,
                status=row["status"],
                response=row["response"],
                timestamp=row["timestamp"],
            )
        )

    return logs


def get_all_webhook_logs(limit: int = 100) -> List[WebhookLog]:
    """Get all webhook logs."""
    db = get_db()

    query = """
        SELECT * FROM webhook_logs
        ORDER BY timestamp DESC
        LIMIT ?
    """
    rows = db.execute(query, (limit,)).fetchall()

    logs = []
    for row in rows:
        payload = json.loads(row["payload"]) if row["payload"] else {}
        logs.append(
            WebhookLog(
                id=row["id"],
                webhook_id=row["webhook_id"],
                payload=payload,
                status=row["status"],
                response=row["response"],
                timestamp=row["timestamp"],
            )
        )

    return logs


def test_webhook_connection(webhook_id: int) -> Dict[str, Any]:
    """Test if a webhook URL is accessible."""
    webhook = get_webhook(webhook_id)
    if not webhook:
        return {"success": False, "message": "Webhook not found"}

    try:
        # Make a HEAD request to the webhook URL to test connectivity
        response = rate_limited_request("HEAD", webhook.url, timeout=10, service_name="webhook")

        return {
            "success": True,
            "status_code": response.status_code,
            "message": f"Webhook URL is accessible (status: {response.status_code})",
        }
    except RateLimitError as e:
        return {"success": False, "message": f"Webhook URL rate limited: {str(e)}"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Webhook URL is not accessible: {str(e)}"}
