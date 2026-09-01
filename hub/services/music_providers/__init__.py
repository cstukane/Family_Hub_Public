"""Package for music provider integrations and state handling."""

from .provider_state import (
    get_active_provider_id,
    load_state,
    save_state,
    set_active_provider_id,
)
from .providers import registry

__all__ = [
    "get_active_provider_id",
    "load_state",
    "save_state",
    "set_active_provider_id",
    "registry",
]
