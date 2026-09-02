"""
Plugin marketplace system for Family Hub.
Handles plugin discovery, installation, and updates.
"""

import json
import logging
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from hub.plugins.base import PluginType
from hub.plugins.manager import PluginManager

logger = logging.getLogger(__name__)


@dataclass
class MarketplacePlugin:
    """Represents a plugin available in the marketplace."""

    name: str
    version: str
    author: str
    description: str
    type: PluginType
    download_url: str
    homepage: Optional[str] = None
    license: Optional[str] = None
    dependencies: List[str] = None
    rating: float = 0.0
    downloads: int = 0
    last_updated: Optional[str] = None
    sha256: Optional[str] = None  # For verification


class PluginMarketplace:
    """
    Manages the plugin marketplace functionality.
    Allows discovering, downloading, and installing plugins from remote sources.
    """

    def __init__(self, plugin_manager: PluginManager, marketplace_url: str = None):
        self.plugin_manager = plugin_manager
        self.marketplace_url = marketplace_url or "https://api.example.com"  # Placeholder
        self.cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_available_plugins(self) -> List[MarketplacePlugin]:
        """
        Get a list of plugins available in the marketplace.

        Returns:
            List of MarketplacePlugin objects
        """
        try:
            # In a real implementation, this would fetch from a remote API
            # For now, we'll return a mock list or check a local file
            mock_plugins = [
                MarketplacePlugin(
                    name="weather-extended",
                    version="1.1.0",
                    author="Community",
                    description="Extended weather information with radar maps",
                    type=PluginType.ADAPTER,
                    download_url="https://example.com/plugins/weather-extended.zip",
                    rating=4.5,
                    downloads=120,
                    last_updated="2024-01-15",
                ),
                MarketplacePlugin(
                    name="smart-home-integration",
                    version="2.0.1",
                    author="SmartHome Co.",
                    description="Integration with popular smart home systems",
                    type=PluginType.INTEGRATION,
                    download_url="https://example.com/plugins/smart-home.zip",
                    homepage="https://smarthome.example.com",
                    rating=4.8,
                    downloads=89,
                    last_updated="2024-01-20",
                ),
            ]
            return mock_plugins
        except Exception:
            # On error, return empty list
            return []

    def get_plugin_details(self, plugin_name: str) -> Optional[MarketplacePlugin]:
        """
        Get detailed information about a specific plugin.

        Args:
            plugin_name: Name of the plugin to get details for

        Returns:
            MarketplacePlugin object if found, None otherwise
        """
        try:
            # In a real implementation, this would fetch from a remote API
            available_plugins = self.get_available_plugins()
            for plugin in available_plugins:
                if plugin.name == plugin_name:
                    return plugin
            return None
        except Exception:
            return None

    def download_plugin(self, plugin_name: str) -> Optional[str]:
        """
        Download a plugin from the marketplace.

        Args:
            plugin_name: Name of the plugin to download

        Returns:
            Path to the downloaded plugin file, None on failure
        """
        try:
            plugin_info = self.get_plugin_details(plugin_name)
            if not plugin_info:
                return None

            # Create temporary file for download
            # temp_file = os.path.join(self.cache_dir, f"{plugin_name}.zip")

            # In a real implementation, this would download from plugin_info.download_url
            # For now, we'll simulate a download
            logger.info("Downloading plugin: %s from %s", plugin_name, plugin_info.download_url)

            # Mock download - in real implementation:
            # response = requests.get(plugin_info.download_url)
            # if response.status_code == 200:
            #     with open(temp_file, 'wb') as f:
            #         f.write(response.content)
            #     return temp_file

            # For now, return None to indicate no real download
            return None
        except Exception:
            logger.exception("Error downloading plugin %s", plugin_name)
            return None

    def install_plugin_from_marketplace(self, plugin_name: str) -> bool:
        """
        Install a plugin from the marketplace.

        Args:
            plugin_name: Name of the plugin to install

        Returns:
            True if installation was successful, False otherwise
        """
        try:
            # First download the plugin
            downloaded_file = self.download_plugin(plugin_name)
            if not downloaded_file:
                return False

            # Verify the download (if checksum is available)
            if downloaded_file and self._verify_download(downloaded_file, plugin_name):
                # Install the plugin
                return self.plugin_manager.install_plugin_from_path(downloaded_file, plugin_name)
            else:
                return False
        except Exception:
            logger.exception("Error installing plugin %s", plugin_name)
            return False

    def _verify_download(self, file_path: str, plugin_name: str) -> bool:
        """
        Verify the integrity of a downloaded plugin file.

        Args:
            file_path: Path to the downloaded file
            plugin_name: Name of the plugin

        Returns:
            True if verification passes, False otherwise
        """
        try:
            # In a real implementation, this would verify a checksum
            # For now, just return True
            return True
        except Exception:
            return False

    def search_plugins(self, query: str) -> List[MarketplacePlugin]:
        """
        Search for plugins in the marketplace.

        Args:
            query: Search query string

        Returns:
            List of matching MarketplacePlugin objects
        """
        try:
            all_plugins = self.get_available_plugins()
            matching_plugins = []

            for plugin in all_plugins:
                if (
                    query.lower() in plugin.name.lower()
                    or query.lower() in plugin.description.lower()
                    or query.lower() in plugin.author.lower()
                ):
                    matching_plugins.append(plugin)

            return matching_plugins
        except Exception:
            return []

    def get_featured_plugins(self) -> List[MarketplacePlugin]:
        """
        Get a list of featured plugins.

        Returns:
            List of featured MarketplacePlugin objects
        """
        try:
            all_plugins = self.get_available_plugins()
            # Sort by rating and downloads to get featured ones
            featured = sorted(all_plugins, key=lambda p: (p.rating, p.downloads), reverse=True)
            return featured[:5]  # Return top 5
        except Exception:
            return []

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[MarketplacePlugin]:
        """
        Get plugins filtered by type.

        Args:
            plugin_type: Type of plugins to return

        Returns:
            List of MarketplacePlugin objects of the specified type
        """
        try:
            all_plugins = self.get_available_plugins()
            return [p for p in all_plugins if p.type == plugin_type]
        except Exception:
            return []

    def check_for_updates(self) -> Dict[str, str]:
        """
        Check for available updates for installed plugins.

        Returns:
            Dictionary mapping plugin names to their latest available versions
        """
        try:
            installed_plugins = self.plugin_manager.get_installed_plugins()
            updates = {}

            for plugin_name in installed_plugins:
                plugin_info = self.get_plugin_details(plugin_name)
                if plugin_info:
                    # Compare installed version with marketplace version
                    installed_version = self.plugin_manager.get_plugin_info(plugin_name).version
                    if self._compare_versions(plugin_info.version, installed_version) > 0:
                        updates[plugin_name] = plugin_info.version

            return updates
        except Exception:
            return {}

    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            1 if version1 > version2, -1 if version1 < version2, 0 if equal
        """
        # Simple version comparison (major.minor.patch)
        v1_parts = [int(x) for x in version1.split(".")]
        v2_parts = [int(x) for x in version2.split(".")]

        for v1, v2 in zip(v1_parts, v2_parts):
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1

        # If all compared parts are equal, check if one has more parts
        if len(v1_parts) > len(v2_parts):
            return 1
        elif len(v1_parts) < len(v2_parts):
            return -1
        else:
            return 0


class LocalPluginRepository:
    """
    Local repository for managing plugin files and installations.
    """

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.plugins_path = self.base_path / "plugins"
        self.downloads_path = self.base_path / "downloads"
        self.backup_path = self.base_path / "backup"

        # Create necessary directories
        self.plugins_path.mkdir(parents=True, exist_ok=True)
        self.downloads_path.mkdir(parents=True, exist_ok=True)
        self.backup_path.mkdir(parents=True, exist_ok=True)

    def get_installed_plugins_info(self) -> List[Dict[str, Any]]:
        """
        Get information about locally installed plugins.

        Returns:
            List of dictionaries with plugin information
        """
        plugins_info = []

        for plugin_dir in self.plugins_path.iterdir():
            if plugin_dir.is_dir():
                # Look for plugin info in a metadata file
                metadata_file = plugin_dir / "plugin.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)
                            plugins_info.append(metadata)
                    except Exception:
                        # If we can't read the metadata, create a basic one
                        plugins_info.append(
                            {
                                "name": plugin_dir.name,
                                "version": "unknown",
                                "status": "installed",
                                "author": "unknown",
                                "description": "No description available",
                            }
                        )
                else:
                    # If no metadata file, create basic info
                    plugins_info.append(
                        {
                            "name": plugin_dir.name,
                            "version": "unknown",
                            "status": "installed",
                            "author": "unknown",
                            "description": "No description available",
                        }
                    )

        return plugins_info

    def backup_plugin(self, plugin_name: str) -> bool:
        """
        Create a backup of a plugin.

        Args:
            plugin_name: Name of the plugin to backup

        Returns:
            True if backup was successful, False otherwise
        """
        try:
            source_path = self.plugins_path / plugin_name
            if not source_path.exists():
                return False

            backup_file = self.backup_path / f"{plugin_name}_backup.zip"

            # Create a zip backup
            with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(source_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.plugins_path)
                        zipf.write(file_path, arcname)

            return True
        except Exception:
            return False

    def remove_plugin(self, plugin_name: str) -> bool:
        """
        Remove a plugin from the local repository.

        Args:
            plugin_name: Name of the plugin to remove

        Returns:
            True if removal was successful, False otherwise
        """
        try:
            plugin_path = self.plugins_path / plugin_name
            if plugin_path.exists():
                import shutil

                shutil.rmtree(plugin_path)
                return True
            return False
        except Exception:
            return False

    def validate_plugin_structure(self, plugin_path: str) -> bool:
        """
        Validate that a plugin has the correct structure.

        Args:
            plugin_path: Path to the plugin directory

        Returns:
            True if structure is valid, False otherwise
        """
        plugin_path = Path(plugin_path)

        # Check for required files
        required_files = ["plugin.py", "plugin.json"]

        for req_file in required_files:
            if not (plugin_path / req_file).exists():
                return False

        # Additional checks can be added here

        return True
