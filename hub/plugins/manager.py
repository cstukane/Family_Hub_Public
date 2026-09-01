"""
Plugin manager for the Family Hub application.
Handles loading, enabling, disabling, and managing plugins.
"""

import importlib.util
import logging
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

from flask import Flask, current_app, has_app_context

from hub.db import get_db
from hub.plugins.base import Plugin, PluginInfo, PluginStatus, PluginType
from hub.plugins.sandbox import PluginSecurityValidator

logger = logging.getLogger(__name__)


@dataclass
class PluginLoadResult:
    """Result of plugin loading operation."""

    success: bool
    message: str
    plugin: Optional[Plugin] = None


class PluginManager:
    """
    Manages the lifecycle of plugins in the Family Hub application.
    Handles loading, enabling, disabling, and unloading of plugins.
    """

    def __init__(self, app: Flask = None):
        self.app = app
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_paths: Dict[str, str] = {}  # plugin_name -> path
        self.plugin_directory = os.path.join(os.path.dirname(__file__), "installed")
        self.allow_unsafe_plugins = False
        self.max_plugins = 100

        # Create the plugins directory if it doesn't exist
        os.makedirs(self.plugin_directory, exist_ok=True)

    def init_app(self, app: Flask) -> None:
        """Initialize with Flask app."""
        self.app = app
        self._apply_config()

    def _apply_config(self) -> None:
        config = None
        if self.app:
            config = self.app.config.get("CONFIG")
        elif has_app_context():
            config = current_app.config.get("CONFIG")

        plugin_config = getattr(config, "plugin_config", None) if config else None
        if plugin_config:
            plugin_dir = getattr(plugin_config, "plugin_directory", None)
            if plugin_dir:
                self.plugin_directory = plugin_dir
                os.makedirs(self.plugin_directory, exist_ok=True)

            self.allow_unsafe_plugins = bool(getattr(plugin_config, "allow_unsafe", False))
            max_plugins = getattr(plugin_config, "max_plugins", self.max_plugins)
            try:
                self.max_plugins = int(max_plugins)
            except (TypeError, ValueError):
                self.max_plugins = 100

    def _log_warning(self, message: str) -> None:
        if self.app:
            self.app.logger.warning(message)
            return
        if has_app_context():
            current_app.logger.warning(message)
            return
        logger.warning(message)

    def _log_error(self, message: str) -> None:
        if self.app:
            self.app.logger.error(message)
            return
        if has_app_context():
            current_app.logger.error(message)
            return
        logger.error(message)

    def _validate_plugin_code(self, plugin_path: str) -> Optional[str]:
        try:
            with open(plugin_path, "r", encoding="utf-8") as handle:
                code = handle.read()
        except OSError as exc:
            return f"Unable to read plugin code: {exc}"

        result = PluginSecurityValidator.validate_plugin_code(code)
        if result.get("valid"):
            return None

        violations = result.get("violations") or []
        error = result.get("error")
        details = ", ".join(violations) if violations else error or "unknown"
        return f"Unsafe plugin code detected: {details}"

    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in the plugin directory.

        Returns:
            List of plugin names discovered
        """
        self._apply_config()
        discovered_plugins = []

        # Create plugin directory if it doesn't exist
        os.makedirs(self.plugin_directory, exist_ok=True)

        for item in os.listdir(self.plugin_directory):
            item_path = os.path.join(self.plugin_directory, item)
            if os.path.isdir(item_path):
                # Check if it contains a plugin.py file
                plugin_file = os.path.join(item_path, "plugin.py")
                if os.path.exists(plugin_file):
                    discovered_plugins.append(item)

        return discovered_plugins

    def load_plugin(self, plugin_name: str) -> PluginLoadResult:
        """
        Load a plugin by name.

        Args:
            plugin_name: Name of the plugin to load

        Returns:
            PluginLoadResult with success status and plugin instance
        """
        try:
            self._apply_config()
            plugin_path = os.path.join(self.plugin_directory, plugin_name, "plugin.py")

            if not os.path.exists(plugin_path):
                return PluginLoadResult(success=False, message=f"Plugin file not found: {plugin_path}")

            validation_error = self._validate_plugin_code(plugin_path)
            if validation_error:
                if self.allow_unsafe_plugins:
                    self._log_warning(f"{validation_error}. allow_unsafe is set, continuing.")
                else:
                    return PluginLoadResult(success=False, message=validation_error)

            # Import the plugin module
            spec = importlib.util.spec_from_file_location(f"{plugin_name}_module", plugin_path)
            if spec is None:
                return PluginLoadResult(success=False, message=f"Could not load spec for plugin: {plugin_name}")

            module = importlib.util.module_from_spec(spec)

            # Add the module to sys.modules so it can be found by other modules
            sys.modules[spec.name] = module

            try:
                spec.loader.exec_module(module)
            except Exception as e:
                return PluginLoadResult(success=False, message=f"Error executing plugin module: {str(e)}")

            # Look for a class that inherits from Plugin
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, Plugin) and attr != Plugin:
                    plugin_class = attr
                    break

            if plugin_class is None:
                return PluginLoadResult(success=False, message=f"No Plugin class found in module: {plugin_name}")

            # Try to get plugin info
            try:
                # Most plugins should have a static method to get info
                if hasattr(plugin_class, "get_plugin_info"):
                    plugin_info = plugin_class.get_plugin_info()
                else:
                    # Default plugin info if the class doesn't provide it
                    plugin_info = PluginInfo(
                        name=plugin_name,
                        version="1.0.0",
                        author="Unknown",
                        description="No description provided",
                        type=PluginType.CUSTOM,
                    )

                # Create plugin instance
                plugin_instance = plugin_class(plugin_info)

                # Store the plugin
                self.plugins[plugin_name] = plugin_instance
                self.plugin_paths[plugin_name] = plugin_path

                return PluginLoadResult(
                    success=True, message=f"Plugin {plugin_name} loaded successfully", plugin=plugin_instance
                )
            except Exception as e:
                return PluginLoadResult(success=False, message=f"Error creating plugin instance: {str(e)}")

        except Exception as e:
            return PluginLoadResult(success=False, message=f"Error loading plugin {plugin_name}: {str(e)}")

    def initialize_plugin(self, plugin_name: str) -> bool:
        """
        Initialize a loaded plugin.

        Args:
            plugin_name: Name of the plugin to initialize

        Returns:
            True if initialization was successful, False otherwise
        """
        if plugin_name not in self.plugins:
            return False

        try:
            plugin = self.plugins[plugin_name]
            return plugin.initialize(self.app)
        except Exception as e:
            self._log_error(f"Error initializing plugin {plugin_name}: {str(e)}")
            return False

    def enable_plugin(self, plugin_name: str) -> bool:
        """
        Enable a plugin.

        Args:
            plugin_name: Name of the plugin to enable

        Returns:
            True if plugin was successfully enabled, False otherwise
        """
        if plugin_name not in self.plugins:
            return False

        try:
            plugin = self.plugins[plugin_name]
            activated = plugin.activate()
            if activated:
                plugin.enabled = True
                # Update status in database if available
                if self.app:
                    db = get_db()
                    if db:
                        db.execute(
                            """INSERT OR REPLACE INTO plugins (name, status)
                               VALUES (?, ?)""",
                            (plugin_name, PluginStatus.ENABLED.value),
                        )
                        db.commit()

                return True
            return False
        except Exception as e:
            self._log_error(f"Error enabling plugin {plugin_name}: {str(e)}")
            return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """
        Disable a plugin.

        Args:
            plugin_name: Name of the plugin to disable

        Returns:
            True if plugin was successfully disabled, False otherwise
        """
        if plugin_name not in self.plugins:
            return False

        try:
            plugin = self.plugins[plugin_name]
            deactivated = plugin.deactivate()
            if deactivated:
                plugin.enabled = False
                # Update status in database if available
                if self.app:
                    db = get_db()
                    if db:
                        db.execute(
                            """INSERT OR REPLACE INTO plugins (name, status)
                               VALUES (?, ?)""",
                            (plugin_name, PluginStatus.DISABLED.value),
                        )
                        db.commit()

                return True
            return False
        except Exception as e:
            self._log_error(f"Error disabling plugin {plugin_name}: {str(e)}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            True if plugin was successfully unloaded, False otherwise
        """
        if plugin_name not in self.plugins:
            return False

        try:
            plugin = self.plugins[plugin_name]

            # First deactivate the plugin
            plugin.deactivate()

            # Call destroy method for cleanup
            plugin.destroy()

            # Remove from our dictionary
            del self.plugins[plugin_name]
            if plugin_name in self.plugin_paths:
                del self.plugin_paths[plugin_name]

            # Remove from sys.modules to fully unload
            module_name = f"{plugin_name}_module"
            if module_name in sys.modules:
                del sys.modules[module_name]

            return True
        except Exception as e:
            self._log_error(f"Error unloading plugin {plugin_name}: {str(e)}")
            return False

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        Get a plugin instance by name.

        Args:
            plugin_name: Name of the plugin to retrieve

        Returns:
            Plugin instance if found, None otherwise
        """
        return self.plugins.get(plugin_name)

    def get_all_plugins(self) -> Dict[str, Plugin]:
        """
        Get all loaded plugins.

        Returns:
            Dictionary mapping plugin names to plugin instances
        """
        return self.plugins.copy()

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """
        Get information about a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            PluginInfo if found, None otherwise
        """
        plugin = self.get_plugin(plugin_name)
        if plugin:
            return plugin.info
        return None

    def get_enabled_plugins(self) -> List[str]:
        """
        Get a list of enabled plugin names.

        Returns:
            List of names of enabled plugins
        """
        return [name for name, plugin in self.plugins.items() if plugin.enabled]

    def install_plugin_from_path(self, source_path: str, plugin_name: str) -> bool:
        """
        Install a plugin from a source path.

        Args:
            source_path: Path to the plugin source
            plugin_name: Name to give the plugin

        Returns:
            True if installation was successful, False otherwise
        """
        try:
            self._apply_config()
            if self.max_plugins > 0 and len(self.discover_plugins()) >= self.max_plugins:
                self._log_warning("Maximum plugin limit reached; cannot install more plugins.")
                return False
            target_path = os.path.join(self.plugin_directory, plugin_name)

            # Create target directory if it doesn't exist
            os.makedirs(target_path, exist_ok=True)

            # Copy plugin files
            import shutil

            if os.path.isdir(source_path):
                # If source is a directory, copy its contents
                for item in os.listdir(source_path):
                    source_item = os.path.join(source_path, item)
                    target_item = os.path.join(target_path, item)
                    if os.path.isdir(source_item):
                        shutil.copytree(source_item, target_item, dirs_exist_ok=True)
                    else:
                        shutil.copy2(source_item, target_item)
            else:
                # If source is a zip file, extract it
                import zipfile

                with zipfile.ZipFile(source_path, "r") as zip_ref:
                    zip_ref.extractall(target_path)

            plugin_entry = os.path.join(target_path, "plugin.py")
            validation_error = self._validate_plugin_code(plugin_entry)
            if validation_error and not self.allow_unsafe_plugins:
                shutil.rmtree(target_path, ignore_errors=True)
                self._log_warning(validation_error)
                return False
            if validation_error and self.allow_unsafe_plugins:
                self._log_warning(f"{validation_error}. allow_unsafe is set, continuing.")

            # Load the newly installed plugin
            result = self.load_plugin(plugin_name)
            return result.success
        except Exception as e:
            self._log_error(f"Error installing plugin {plugin_name}: {str(e)}")
            return False

    def get_installed_plugins(self) -> List[str]:
        """
        Get list of installed plugin names.

        Returns:
            List of installed plugin names
        """
        return self.discover_plugins()


# Global plugin manager instance
plugin_manager = PluginManager()
