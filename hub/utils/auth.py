import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

_CACHED_MEDIA_SECRET: Optional[str] = None


class AuthError(ValueError):
    """Raised when authentication fails."""


def _get_env_value(name: str) -> Optional[str]:
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def get_media_launcher_secret() -> str:
    """Get the shared secret used to sign media launcher tokens."""
    global _CACHED_MEDIA_SECRET
    secret = _get_env_value("MEDIA_LAUNCHER_JWT_SECRET") or _get_env_value("SECRET_KEY")
    if secret:
        _CACHED_MEDIA_SECRET = secret
        return secret
    if _CACHED_MEDIA_SECRET:
        return _CACHED_MEDIA_SECRET
    # Generate a process-local secret when no env is provided.
    _CACHED_MEDIA_SECRET = secrets.token_urlsafe(48)
    return _CACHED_MEDIA_SECRET


def generate_media_launcher_token(
    subject: str = "hub-ui",
    ttl_seconds: int = 300,
    secret: Optional[str] = None,
) -> str:
    """Generate a short-lived JWT for the media launcher service."""
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,
        "iss": "family_hub",
        "aud": "media_launcher",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, secret or get_media_launcher_secret(), algorithm="HS256")


def verify_media_launcher_token(token: str, secret: Optional[str] = None) -> Dict[str, Any]:
    """Verify a media launcher JWT and return its payload."""
    try:
        payload = jwt.decode(
            token,
            secret or get_media_launcher_secret(),
            algorithms=["HS256"],
            audience="media_launcher",
            issuer="family_hub",
        )
        return payload
    except jwt.PyJWTError as exc:
        raise AuthError("invalid-token") from exc


def extract_bearer_token(header_value: Optional[str]) -> Optional[str]:
    if not header_value:
        return None
    parts = header_value.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None
