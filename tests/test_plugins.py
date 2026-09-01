"""
Tests for the Family Hub plugin system.
"""

import json
import os
import shutil
import unittest
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from hub.plugins.base import Plugin, PluginInfo, PluginStatus, PluginType
from hub.plugins.manager import PluginLoadResult, PluginManager
from hub.plugins.marketplace import MarketplacePlugin, PluginMarketplace
from hub.plugins.sandbox import PluginSandbox, plugin_sandbox

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / "instance" / "test_tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_test_dir(prefix: str) -> str:
    path = TEST_TMP_ROOT / f"{prefix}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return str(path)


class TestPlugin(unittest.TestCase):
    """Test the base plugin class."""

    def test_plugin_interface(self):
        """Test that the abstract plugin class works correctly."""
        # This should raise an error since Plugin is abstract
        with self.assertRaises(TypeError):
            Plugin(PluginInfo(name="test", version="1.0.0", author="test", description="test", type=PluginType.SERVICE))


class SimpleTestPlugin(Plugin):
    """A simple test plugin implementation."""

    def __init__(self, plugin_info: PluginInfo):
        super().__init__(plugin_info)
        self.initialized = False
        self.activated = False
        self.deactivated = False

    def initialize(self, app_context) -> bool:
        self.initialized = True
        return True

    def activate(self) -> bool:
        self.activated = True
        return True

    def deactivate(self) -> bool:
        self.deactivated = True
        return True


class TestPluginManager(unittest.TestCase):
    """Test the plugin manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        from flask import Flask

        app = Flask(__name__)
        self.plugin_manager = PluginManager()
        self.plugin_manager.init_app(app)

    def test_plugin_manager_initialization(self):
        """Test that plugin manager initializes correctly."""
        self.assertIsNotNone(self.plugin_manager)
        self.assertEqual(len(self.plugin_manager.plugins), 0)

    def test_discover_plugins(self):
        """Test plugin discovery."""
        temp_dir = _make_test_dir("plugin_discover")
        try:
            # Create a plugin directory structure
            plugin_dir = os.path.join(temp_dir, "test_plugin")
            os.makedirs(plugin_dir)

            # Create a basic plugin file
            plugin_file = os.path.join(plugin_dir, "plugin.py")
            with open(plugin_file, "w") as f:
                f.write(
                    """
from hub.plugins.base import Plugin, PluginInfo, PluginType

class TestPlugin(Plugin):
    def __init__(self, plugin_info):
        super().__init__(plugin_info)

    def initialize(self, app_context):
        return True

    def activate(self):
        return True

    def deactivate(self):
        return True
"""
                )

            # Update the plugin manager's directory
            original_dir = self.plugin_manager.plugin_directory
            self.plugin_manager.plugin_directory = temp_dir

            try:
                plugins = self.plugin_manager.discover_plugins()
                self.assertIn("test_plugin", plugins)
            finally:
                self.plugin_manager.plugin_directory = original_dir
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_load_plugin(self):
        """Test loading a plugin."""
        temp_dir = _make_test_dir("plugin_load")
        try:
            # Create a plugin directory structure
            plugin_dir = os.path.join(temp_dir, "simple_test_plugin")
            os.makedirs(plugin_dir)

            # Create a basic plugin file
            plugin_file = os.path.join(plugin_dir, "plugin.py")
            with open(plugin_file, "w") as f:
                f.write(
                    """
from hub.plugins.base import Plugin as BasePlugin, PluginInfo, PluginType

class Plugin(BasePlugin):
    def __init__(self, plugin_info):
        super().__init__(plugin_info)

    def initialize(self, app_context):
        return True

    def activate(self):
        return True

    def deactivate(self):
        return True

    def get_metadata(self):
        return {
            'name': self.info.name,
            'version': self.info.version,
            'author': self.info.author,
            'description': self.info.description,
            'type': self.info.type.value,
            'status': self.info.status.value
        }

    @staticmethod
    def get_plugin_info():
        return PluginInfo(
            name="simple_test_plugin",
            version="1.0.0",
            author="test",
            description="A simple test plugin",
            type=PluginType.SERVICE
        )
"""
                )

            # Update the plugin manager's directory
            original_dir = self.plugin_manager.plugin_directory
            self.plugin_manager.plugin_directory = temp_dir

            try:
                result = self.plugin_manager.load_plugin("simple_test_plugin")
                if not result.success:
                    print(f"Plugin load failed: {result.message}")
                self.assertTrue(result.success, f"Plugin load failed: {result.message}")
                self.assertIsNotNone(result.plugin)
                self.assertIn("simple_test_plugin", self.plugin_manager.plugins)
            finally:
                self.plugin_manager.plugin_directory = original_dir
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestPluginSandbox(unittest.TestCase):
    """Test the plugin sandbox functionality."""

    def test_sandbox_creation(self):
        """Test creating a plugin sandbox."""
        sandbox = PluginSandbox("test_plugin")
        self.assertIsNotNone(sandbox)
        self.assertTrue(os.path.exists(sandbox.sandbox_dir))
        sandbox.cleanup()

    def test_safe_code_execution(self):
        """Test executing safe code in the sandbox."""
        with plugin_sandbox("test_safe_exec") as sandbox:
            code = "result = 2 + 2"
            result = sandbox.execute_code(code)

            self.assertTrue(result["success"])
            self.assertIsNone(result["error"])
            self.assertIsNotNone(result["result"])

    def test_dangerous_code_detection(self):
        """Test that dangerous code is detected."""
        with plugin_sandbox("test_dangerous_exec") as sandbox:
            # Try to import a dangerous module
            code = "import os"
            result = sandbox.execute_code(code)

            self.assertFalse(result["success"])
            self.assertIsNotNone(result["error"])
            self.assertIn("unsafe", result["error"].lower())

    def test_file_access_validation(self):
        """Test that file access is validated."""
        with plugin_sandbox("test_file_access") as sandbox:
            # This should be valid (within sandbox)
            valid_path = os.path.join(sandbox.sandbox_dir, "test.txt")
            self.assertTrue(sandbox.validate_file_access(valid_path))

            # This should be invalid (outside sandbox)
            invalid_path = "/tmp/outside_sandbox.txt"  # Use temp dir for test
            self.assertFalse(sandbox.validate_file_access(invalid_path))


class TestPluginMarketplace(unittest.TestCase):
    """Test the plugin marketplace functionality."""

    def setUp(self):
        """Set up test fixtures."""
        from flask import Flask

        app = Flask(__name__)
        self.plugin_manager = PluginManager()
        self.plugin_manager.init_app(app)
        self.marketplace = PluginMarketplace(self.plugin_manager)

    def test_get_available_plugins(self):
        """Test getting available plugins."""
        plugins = self.marketplace.get_available_plugins()
        # Should return a list, even if empty
        self.assertIsInstance(plugins, list)

    def test_search_plugins(self):
        """Test searching for plugins."""
        results = self.marketplace.search_plugins("test")
        # Should return a list
        self.assertIsInstance(results, list)

    def test_get_featured_plugins(self):
        """Test getting featured plugins."""
        featured = self.marketplace.get_featured_plugins()
        # Should return a list
        self.assertIsInstance(featured, list)


class TestMarketplacePlugin(unittest.TestCase):
    """Test the MarketplacePlugin class."""

    def test_marketplace_plugin_creation(self):
        """Test creating a marketplace plugin."""
        plugin = MarketplacePlugin(
            name="test_plugin",
            version="1.0.0",
            author="test",
            description="A test plugin",
            type=PluginType.SERVICE,
            download_url="http://example.com/plugin.zip",
        )

        self.assertEqual(plugin.name, "test_plugin")
        self.assertEqual(plugin.version, "1.0.0")
        self.assertEqual(plugin.type, PluginType.SERVICE)


if __name__ == "__main__":
    unittest.main()
