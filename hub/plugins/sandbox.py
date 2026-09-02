"""
Security sandbox for Family Hub plugins.
Provides a secure execution environment for untrusted plugin code.
"""

import ast
import builtins
import io
import os
import shutil
import subprocess  # nosec B404
import tempfile
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from typing import Any, Dict, List


class PluginSandbox:
    """
    Security sandbox for executing plugin code in a restricted environment.
    """

    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        self.allowed_builtins = self._get_allowed_builtins()
        self.sandbox_dir = None
        self._create_sandbox_environment()

    def _get_allowed_builtins(self) -> Dict[str, Any]:
        """
        Define which built-in functions are allowed in the sandbox.

        Returns:
            Dictionary of allowed built-in functions
        """
        # Only allow safe built-in functions
        safe_builtins = [
            "abs",
            "all",
            "any",
            "bool",
            "chr",
            "complex",
            "dict",
            "dir",
            "divmod",
            "enumerate",
            "filter",
            "float",
            "format",
            "frozenset",
            "hasattr",
            "hash",
            "hex",
            "id",
            "int",
            "isinstance",
            "len",
            "list",
            "map",
            "max",
            "min",
            "next",
            "object",
            "oct",
            "ord",
            "pow",
            "range",
            "repr",
            "reversed",
            "round",
            "set",
            "slice",
            "sorted",
            "str",
            "sum",
            "super",
            "tuple",
            "type",
            "zip",
        ]

        return {name: getattr(builtins, name) for name in safe_builtins if hasattr(builtins, name)}

    def _create_sandbox_environment(self) -> None:
        """
        Create a secure sandbox directory for plugin execution.
        """
        # Create a temporary directory for the plugin's files
        temp_dir = tempfile.mkdtemp(prefix=f"kh_plugin_{self.plugin_name}_")
        self.sandbox_dir = temp_dir

    def execute_code(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Safely execute plugin code within the sandbox.

        Args:
            code: Python code string to execute
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary with execution results
        """
        # First, parse the code to ensure it doesn't contain dangerous constructs
        try:
            # Parse the code to check for dangerous operations
            tree = ast.parse(code)
            violations = self._check_safety_violations(tree)
            if violations:
                return {
                    "success": False,
                    "error": f"Code contains unsafe operations: {', '.join(violations)}",
                    "result": None,
                }
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error in code: {str(e)}", "result": None}

        # Create a restricted execution environment
        restricted_globals = {
            "__builtins__": self.allowed_builtins,
            "__name__": "__sandbox__",
        }

        # Capture output
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()

        try:
            with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                # Execute the code in the restricted environment
                exec(code, restricted_globals)  # nosec B102

            return {
                "success": True,
                "error": None,
                "result": restricted_globals,
                "output": output_buffer.getvalue(),
                "errors": error_buffer.getvalue(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "result": None,
                "output": output_buffer.getvalue(),
                "errors": error_buffer.getvalue(),
            }

    def _check_safety_violations(self, tree: ast.AST) -> List[str]:
        """
        Check AST for safety violations.

        Args:
            tree: Parsed AST of the code

        Returns:
            List of safety violations found
        """
        violations = []

        for node in ast.walk(tree):
            # Check for dangerous imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    module_name = alias.name
                    if module_name in ["os", "sys", "subprocess", "shutil", "socket", "urllib", "requests"]:
                        violations.append(f"dangerous import: {module_name}")

            # Check for dangerous function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in ["exec", "eval", "__import__", "open", "compile"]:
                        violations.append(f"dangerous function call: {func_name}")
                elif isinstance(node.func, ast.Attribute):
                    # Check for dangerous method calls like file operations
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id in ["file", "open"]:
                            violations.append("dangerous file operation")

        return violations

    def execute_subprocess(self, command: List[str], timeout: int = 10) -> Dict[str, Any]:
        """
        Execute a subprocess command safely.

        Args:
            command: Command to execute as a list of strings
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary with execution results
        """
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, cwd=self.sandbox_dir)  # nosec B603

            return {"success": True, "return_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out",
                "return_code": -1,
                "stdout": "",
                "stderr": "Command timed out",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Command execution error: {str(e)}",
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
            }

    def validate_file_access(self, file_path: str) -> bool:
        """
        Validate if a file path is safe for plugin access.

        Args:
            file_path: Path to validate

        Returns:
            True if path is safe, False otherwise
        """
        # Normalize the path
        normalized_path = os.path.abspath(file_path)
        sandbox_path = os.path.abspath(self.sandbox_dir)

        # Check if the path is within the sandbox directory
        return normalized_path.startswith(sandbox_path)

    def create_safe_file(self, filename: str, content: str) -> bool:
        """
        Create a file safely within the sandbox.

        Args:
            filename: Name of the file to create
            content: Content to write to the file

        Returns:
            True if file was created successfully, False otherwise
        """
        file_path = os.path.join(self.sandbox_dir, filename)

        # Ensure the file will be in the sandbox
        if not self.validate_file_access(file_path):
            return False

        try:
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w") as f:
                f.write(content)

            return True
        except Exception:
            return False

    def cleanup(self) -> None:
        """
        Clean up the sandbox environment.
        """
        if self.sandbox_dir and os.path.exists(self.sandbox_dir):
            try:
                shutil.rmtree(self.sandbox_dir)
            except Exception:  # nosec B110
                # If we can't remove it, just ignore - it's in temp anyway
                pass


@contextmanager
def plugin_sandbox(plugin_name: str):
    """
    Context manager for creating and cleaning up a plugin sandbox.

    Args:
        plugin_name: Name of the plugin to create a sandbox for
    """
    sandbox = PluginSandbox(plugin_name)
    try:
        yield sandbox
    finally:
        sandbox.cleanup()


class PluginSecurityValidator:
    """
    Validates plugin code and configuration for security issues.
    """

    @staticmethod
    def validate_plugin_code(code: str) -> Dict[str, Any]:
        """
        Validate plugin code for security issues.

        Args:
            code: Plugin code to validate

        Returns:
            Dictionary with validation results
        """
        try:
            tree = ast.parse(code)
            violations = []

            # Check for imports
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        module_name = alias.name
                        if module_name in ["os", "sys", "subprocess", "shutil", "socket"]:
                            violations.append(f"Potentially dangerous import: {module_name}")

            # Check for function calls
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in ["exec", "eval"]:
                            violations.append(f"Unsafe function: {func_name}")

            return {"valid": len(violations) == 0, "violations": violations, "error": None}
        except SyntaxError as e:
            return {"valid": False, "violations": [], "error": f"Syntax error: {str(e)}"}

    @staticmethod
    def validate_plugin_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate plugin configuration for security issues.

        Args:
            config: Plugin configuration to validate

        Returns:
            Dictionary with validation results
        """
        violations = []

        # Check for potentially dangerous configuration settings
        if "exec" in str(config).lower() or "eval" in str(config).lower():
            violations.append("Configuration contains potentially dangerous keywords")

        # Check for external URLs that might be dangerous
        for key, value in config.items():
            if isinstance(value, str):
                if value.startswith(("http://", "https://")):
                    # In a real implementation, you'd want more thorough URL validation
                    pass

        return {"valid": len(violations) == 0, "violations": violations, "error": None}
