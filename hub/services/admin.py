"""Admin service for the Family Hub application."""

import os
import shutil
from datetime import datetime
from typing import Any, Dict

from flask import current_app, session
from werkzeug.security import check_password_hash, generate_password_hash

from hub.config import load_config
from hub.db import get_db
from hub.utils.http import RateLimitError, rate_limited_get


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return check_password_hash(password_hash, password)


def is_admin_authenticated() -> bool:
    """Check if admin is currently authenticated."""
    return session.get("admin_authenticated", False)


def authenticate_admin(username: str, password: str) -> bool:
    """Authenticate admin user with username and password."""
    config = current_app.config.get("CONFIG")
    if not config or not config.security.admin_enabled:
        return False

    # Check against stored credentials
    if (
        config.security.admin_username == username
        and config.security.admin_password_hash
        and verify_password(password, config.security.admin_password_hash)
    ):
        session["admin_authenticated"] = True
        session["admin_username"] = username
        session.permanent = True  # Use permanent session with timeout
        return True

    return False


def logout_admin() -> None:
    """Logout the admin user."""
    session.pop("admin_authenticated", None)
    session.pop("admin_username", None)


def check_admin_auth_required(f):
    """Decorator to check if admin authentication is required for an endpoint."""

    def decorated_function(*args, **kwargs):
        if not is_admin_authenticated():
            from flask import abort

            abort(401, description="Admin authentication required")
        return f(*args, **kwargs)

    return decorated_function


def get_config_for_admin() -> Dict[str, Any]:
    """Get configuration for admin panel (excluding sensitive data)."""
    config = current_app.config.get("CONFIG")
    if not config:
        return {}

    # Convert config to dict but exclude sensitive fields
    config_dict = config.model_dump()

    # Remove sensitive data
    if "security" in config_dict:
        if "admin_password_hash" in config_dict["security"]:
            del config_dict["security"]["admin_password_hash"]

    return config_dict


def update_config_from_admin(new_config: Dict[str, Any]) -> bool:
    """Update configuration from admin panel."""
    try:
        # Get current config path
        config_path = current_app.config.get("CONFIG_PATH", "config.yaml")

        # Create backup of current config
        backup_path = f"{config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(config_path, backup_path)

        # Load current config and update with new values
        current_config = load_config(config_path).model_dump()

        # Update only allowed fields (avoid security fields for now)
        # For safety, we'll only allow updating non-security related configs
        allowed_fields = ["layout", "apps", "providers", "features", "ui"]

        for field in allowed_fields:
            if field in new_config:
                current_config[field] = new_config[field]

        # Write updated config back to file
        with open(config_path, "w", encoding="utf-8") as f:
            import yaml

            yaml.dump(current_config, f, default_flow_style=False)

        return True
    except Exception as e:
        current_app.logger.error(f"Error updating config from admin: {e}")
        return False


def get_system_info() -> Dict[str, Any]:
    """Get system information for admin panel."""
    import platform

    import psutil

    from hub import __version__

    try:
        # Get system stats
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk_usage = psutil.disk_usage("/")

        # Get process info
        process = psutil.Process()
        process_memory = process.memory_info().rss / 1024 / 1024  # MB

        return {
            "application": {
                "version": __version__,
                "name": "Family Hub",
                "environment": os.environ.get("FLASK_ENV", "production"),
            },
            "system": {
                "platform": platform.platform(),
                "processor": platform.processor() or platform.machine(),
                "python_version": platform.python_version(),
                "cpu_percent": cpu_percent,
                "memory_total": memory.total / (1024**3),  # GB
                "memory_available": memory.available / (1024**3),  # GB
                "memory_percent": memory.percent,
                "disk_total": disk_usage.total / (1024**3),  # GB
                "disk_used": disk_usage.used / (1024**3),  # GB
                "disk_percent": disk_usage.percent,
                "process_memory_mb": round(process_memory, 2),
            },
            "runtime": {
                "start_time": getattr(current_app, "start_time", datetime.now().isoformat()),
                "uptime_seconds": getattr(current_app, "uptime_seconds", 0),
            },
        }
    except Exception as e:
        current_app.logger.error(f"Error getting system info: {e}")
        return {"error": "Could not retrieve system information"}


def run_diagnostics() -> Dict[str, Any]:
    """Run system diagnostics."""
    diagnostics = {"timestamp": datetime.now().isoformat(), "checks": {}}

    # Check database connectivity
    try:
        db = get_db()
        db.execute("SELECT 1")
        diagnostics["checks"]["database"] = {"status": "ok", "message": "Database connection successful"}
    except Exception as e:
        diagnostics["checks"]["database"] = {"status": "error", "message": str(e)}

    # Check cache functionality
    try:
        from hub.cache import get_cache, set_cache

        test_key = "diagnostic_test"
        set_cache(test_key, "test_value", 60)
        cache_result = get_cache(test_key)
        if cache_result == "test_value":
            diagnostics["checks"]["cache"] = {"status": "ok", "message": "Cache working properly"}
        else:
            diagnostics["checks"]["cache"] = {"status": "error", "message": "Cache not returning expected value"}
    except Exception as e:
        diagnostics["checks"]["cache"] = {"status": "error", "message": str(e)}

    # Check scheduler status
    try:
        scheduler_running = hasattr(current_app, "scheduler") and current_app.scheduler.running
        if scheduler_running:
            diagnostics["checks"]["scheduler"] = {"status": "ok", "message": "Scheduler running"}
        else:
            diagnostics["checks"]["scheduler"] = {"status": "warning", "message": "Scheduler not running"}
    except Exception as e:
        diagnostics["checks"]["scheduler"] = {"status": "error", "message": str(e)}

    # Check network connectivity (simple check)
    try:
        response = rate_limited_get("https://httpbin.org/get", timeout=5, service_name="diagnostics")
        if response.status_code == 200:
            diagnostics["checks"]["network"] = {"status": "ok", "message": "Network connectivity verified"}
        else:
            diagnostics["checks"]["network"] = {
                "status": "warning",
                "message": f"Network request failed with status {response.status_code}",
            }
    except RateLimitError as e:
        diagnostics["checks"]["network"] = {"status": "warning", "message": f"Network rate limited: {str(e)}"}
    except Exception as e:
        diagnostics["checks"]["network"] = {"status": "warning", "message": f"Network check failed: {str(e)}"}

    # Check for the external services that the app uses
    config = current_app.config.get("CONFIG")
    if config and hasattr(config, "providers"):
        # Check weather service
        try:
            from hub.services import weather

            weather_data = weather.get_weather_data()
            if weather_data and "error" not in weather_data:
                diagnostics["checks"]["weather_service"] = {"status": "ok", "message": "Weather service accessible"}
            else:
                diagnostics["checks"]["weather_service"] = {
                    "status": "error",
                    "message": "Weather service not responding",
                }
        except Exception as e:
            diagnostics["checks"]["weather_service"] = {
                "status": "error",
                "message": f"Weather service error: {str(e)}",
            }

        # Check calendar service
        try:
            from datetime import timedelta

            from hub.services import calendar

            now = datetime.now()
            future = now + timedelta(days=7)
            events = calendar.list_events(now, future)
            if events is not None:
                diagnostics["checks"]["calendar_service"] = {"status": "ok", "message": "Calendar service accessible"}
            else:
                diagnostics["checks"]["calendar_service"] = {
                    "status": "error",
                    "message": "Calendar service not responding",
                }
        except Exception as e:
            diagnostics["checks"]["calendar_service"] = {
                "status": "error",
                "message": f"Calendar service error: {str(e)}",
            }

    return diagnostics
