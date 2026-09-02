import time
from functools import wraps

from flask import abort, current_app, request


def check_rate_limit(limit_type="default"):
    """Check if request is within rate limits based on configuration."""
    if current_app.config.get("TESTING"):
        return
    config = current_app.config.get("CONFIG")
    if not config or not config.security.rate_limit_enabled:
        return  # Rate limiting disabled

    # Get client IP
    client_ip = request.environ.get("HTTP_X_REAL_IP", request.remote_addr)

    # Initialize rate limit data in memory for this session (simplified approach)
    if not hasattr(current_app, "rate_limits"):
        current_app.rate_limits = {}

    current_time = time.time()
    time_window = 60  # 1 minute window for default limit

    # Determine which rate limit to apply
    def _parse_limit(raw_value, fallback):
        if isinstance(raw_value, int):
            return raw_value
        if isinstance(raw_value, str):
            parts = raw_value.split()
            if parts:
                try:
                    return int(parts[0])
                except ValueError:
                    return fallback
        return fallback

    if limit_type == "admin":
        limit = _parse_limit(config.security.admin_rate_limit, 10)
        time_window = 60  # 1 minute for admin limit
    else:
        limit = _parse_limit(config.security.default_rate_limit, 60)
        time_window = 60  # 1 minute for default limit

    # Create key for this IP and limit type
    key = f"{client_ip}_{limit_type}"

    # Get existing requests for this IP
    requests = current_app.rate_limits.get(key, [])

    # Filter requests in the current time window
    requests = [req_time for req_time in requests if current_time - req_time < time_window]

    # Check if limit exceeded
    if len(requests) >= limit:
        abort(429, description=f"Rate limit exceeded: {limit} requests per minute")

    # Add current request to the list
    requests.append(current_time)
    current_app.rate_limits[key] = requests


def require_admin_rate_limit(f):
    """Decorator to apply admin rate limiting to sensitive endpoints."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        check_rate_limit("admin")
        return f(*args, **kwargs)

    return decorated_function


def require_default_rate_limit(f):
    """Decorator to apply default rate limiting to general endpoints."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        check_rate_limit("default")
        return f(*args, **kwargs)

    return decorated_function


def require_ip_whitelist(f):
    """Decorator to check if request comes from whitelisted IP for admin functions."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app.config.get("TESTING"):
            return f(*args, **kwargs)
        config = current_app.config.get("CONFIG")
        whitelist = []
        trusted_proxies = []
        if config and getattr(config, "security", None):
            whitelist = getattr(config.security, "ip_whitelist", []) or []
            if not isinstance(whitelist, (list, tuple, set)):
                whitelist = []
            trusted_proxies = getattr(config.security, "trusted_proxies", []) or []
            if isinstance(trusted_proxies, str):
                trusted_proxies = [ip.strip() for ip in trusted_proxies.split(",") if ip.strip()]
            if not isinstance(trusted_proxies, (list, tuple, set)):
                trusted_proxies = []

        if config and config.security.ip_whitelist_enabled and whitelist:
            client_ip = request.remote_addr
            if trusted_proxies and client_ip in trusted_proxies:
                forwarded_for = request.headers.get("X-Forwarded-For", "")
                if forwarded_for:
                    client_ip = forwarded_for.split(",")[0].strip()

            # Check if client IP is in whitelist
            if client_ip not in whitelist:
                abort(403, description=f"Access denied: IP {client_ip} not in whitelist")

        return f(*args, **kwargs)

    return decorated_function
