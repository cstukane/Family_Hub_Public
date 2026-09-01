"""
Test suite for Family Hub application.

This test suite covers:
- Configuration loading and validation
- Database initialization and structure
- Service layer functionality
- API endpoints and routes
- Partial templates rendering

To run all tests:
    pytest

To run specific test file:
    pytest tests/test_filename.py

To run with coverage:
    pytest --cov=hub --cov-report=html
"""

# This file can be used to run all tests at once
import subprocess
import sys


def run_all_tests():
    """Run all tests in the suite."""
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], check=False)
    return result.returncode


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
