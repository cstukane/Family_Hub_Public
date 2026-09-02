"""
Base classes and interfaces for the Family Hub plugin system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class PluginType(Enum):
    """Enumeration of plugin types."""

    SERVICE = "service"
    ADAPTER = "adapter"
    UI = "ui"
    INTEGRATION = "integration"
    CUSTOM = "custom"


class PluginStatus(Enum):
    """Enumeration of plugin statuses."""

    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    BROKEN = "broken"
    UPDATING = "updating"


@dataclass
class PluginInfo:
    """Information about a plugin."""

    name: str
    version: str
    author: str
    description: str
    type: PluginType
    homepage: Optional[str] = None
    license: Optional[str] = None
    dependencies: List[str] = None
    status: PluginStatus = PluginStatus.INSTALLED


class Plugin(ABC):
    """
    Abstract base class for all plugins.
    All plugins must inherit from this class and implement required methods.
    """

    def __init__(self, plugin_info: PluginInfo):
        self.info = plugin_info
        self.enabled = False

    @abstractmethod
    def initialize(self, app_context: Any) -> bool:
        """
        Initialize the plugin with the application context.

        Args:
            app_context: The application context

        Returns:
            True if initialization was successful, False otherwise
        """
        pass

    @abstractmethod
    def activate(self) -> bool:
        """
        Activate the plugin.

        Returns:
            True if activation was successful, False otherwise
        """
        pass

    @abstractmethod
    def deactivate(self) -> bool:
        """
        Deactivate the plugin.

        Returns:
            True if deactivation was successful, False otherwise
        """
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the plugin.

        Returns:
            Dictionary containing plugin metadata
        """
        return {
            "name": self.info.name,
            "version": self.info.version,
            "author": self.info.author,
            "description": self.info.description,
            "type": self.info.type.value,
            "status": self.info.status.value,
        }

    def destroy(self) -> bool:
        """
        Clean up the plugin before removal.
        This method is called when the plugin is being unloaded.

        Returns:
            True if cleanup was successful, False otherwise
        """
        return True


class PluginConfig(ABC):
    """
    Base class for plugin configuration.
    Plugins can inherit this to define their configuration schema.
    """

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the configuration schema for this plugin.

        Returns:
            Dictionary representing the configuration schema
        """
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate the provided configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if configuration is valid, False otherwise
        """
        pass


class PluginServiceInterface(ABC):
    """
    Interface that plugins can implement to provide services to the application.
    """

    @abstractmethod
    def register_routes(self, app: Any) -> None:
        """
        Register routes that this plugin provides.

        Args:
            app: The Flask application instance
        """
        pass

    @abstractmethod
    def register_templates(self, template_loader: Any) -> None:
        """
        Register templates that this plugin provides.

        Args:
            template_loader: The template loader instance
        """
        pass
