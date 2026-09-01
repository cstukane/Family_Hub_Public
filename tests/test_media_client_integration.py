"""
Test for media-client.js integration
This test verifies that the media-client.js file has the required functions
"""

import os
import re
import sys


def test_media_client_js():
    """Test that media-client.js has the required functions and structure"""

    # Path to the media-client.js file
    js_file_path = "hub_ui/js/media-client.js"

    if not os.path.exists(js_file_path):
        print(f"ERROR: {js_file_path} does not exist")
        return False

    with open(js_file_path, "r") as f:
        content = f.read()

    # Check for required functions
    required_functions = ["openMedia", "closeMedia", "openMediaWithController"]

    print("Testing media-client.js for required functions...")

    for func_name in required_functions:
        if (
            f"function {func_name}" in content
            or f"async function {func_name}" in content
            or f"const {func_name}" in content
        ):
            print(f"[PASS] {func_name} function found")
        else:
            print(f"[FAIL] {func_name} function NOT found")
            return False

    # Check for domain validation
    if "ALLOWED_DOMAINS" in content and "hostname.endsWith" in content:
        print("[PASS] Domain validation found")
    else:
        print("[FAIL] Domain validation NOT found")
        return False

    # Check for POST requests to media_launcher endpoints
    if "'http://127.0.0.1:7666/v1/open_media'" in content and "'http://127.0.0.1:7666/v1/close_media'" in content:
        print("[PASS] POST requests to media_launcher endpoints found")
    else:
        print("[FAIL] POST requests to media_launcher endpoints NOT found")
        return False

    # Check for error handling
    if "try {" in content and "catch" in content:
        print("[PASS] Error handling found")
    else:
        print("[FAIL] Error handling NOT found")
        return False

    # Check for user-facing alerts
    if "alert(" in content:
        print("[PASS] User-facing alerts found")
    else:
        print("[FAIL] User-facing alerts NOT found")
        return False

    # Check for dev fallback comment
    if "dev-frame" in content and "iframe" in content:
        print("[PASS] Dev fallback (commented) found")
    else:
        print("[FAIL] Dev fallback (commented) NOT found")
        return False

    print("\n[SUCCESS] All media-client.js tests passed!")
    return True


def test_index_html_integration():
    """Test that index.html has the required integration points"""

    html_file_path = "hub_ui/index.html"

    if not os.path.exists(html_file_path):
        print(f"ERROR: {html_file_path} does not exist")
        return False

    with open(html_file_path, "r") as f:
        content = f.read()

    print("\nTesting index.html for client integration...")

    # Check for script inclusion
    if "js/media-client.js" in content:
        print("[PASS] media-client.js script included")
    else:
        print("[FAIL] media-client.js script NOT included")
        return False

    # Check for media buttons that call openMedia
    if 'onclick="openMedia(' in content or "onclick=&quot;openMedia(" in content:
        print("[PASS] Taskbar icons hooked to call openMedia")
    else:
        print("[FAIL] Taskbar icons NOT hooked to call openMedia")
        return False

    # Check for close button
    if 'onclick="closeMedia()' in content or "onclick=&quot;closeMedia()" in content:
        print("[PASS] Close button hooked to call closeMedia")
    else:
        print("[FAIL] Close button NOT hooked to call closeMedia")
        return False

    # Check for dev fallback iframe (commented)
    if '<iframe id="dev-frame"' in content:
        print("[PASS] Dev fallback iframe found (commented out)")
    else:
        print("[FAIL] Dev fallback iframe NOT found")
        return False

    print("[SUCCESS] All index.html integration tests passed!")
    return True


def main():
    """Run all client integration tests"""
    print("Running client integration tests...\n")

    js_test_passed = test_media_client_js()
    html_test_passed = test_index_html_integration()

    if js_test_passed and html_test_passed:
        print("\n[SUCCESS] All client integration tests PASSED!")
        return True
    else:
        print("\n[FAILURE] Some client integration tests FAILED!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
