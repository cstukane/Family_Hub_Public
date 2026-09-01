"""
Media Launcher Service

This service manages child windows for media applications.
It handles spawning and killing media windows as needed.
"""

import atexit
import json
import logging
import os
import shutil
import signal
import subprocess  # nosec B404
import sys
import time
from urllib.parse import urlparse

import psutil
from flask import Flask, jsonify, request

from hub.config import load_config
from hub.utils.auth import AuthError, extract_bearer_token, get_media_launcher_secret, verify_media_launcher_token


def _env_truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


# Configuration for authentication (can be set via environment variable)
LEGACY_AUTH_TOKEN = os.environ.get("MEDIA_HUB_AUTH_TOKEN")
ALLOW_LEGACY_AUTH = _env_truthy(os.environ.get("MEDIA_LAUNCHER_ALLOW_LEGACY_AUTH"))
_MEDIA_LAUNCHER_SECRET = get_media_launcher_secret()

# Per-platform browser binary path (adjust if needed)
# Windows testing: prefer full Chrome path if Chromium not installed
CHROME_WIN = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_LINUX = "/usr/bin/chromium-browser"  # common on Pi OS
CHROME_GENERIC = "chromium"  # fallback


def require_auth(f):
    """Decorator to require authentication token."""

    def decorated_function(*args, **kwargs):
        bearer = extract_bearer_token(request.headers.get("Authorization"))
        if bearer:
            try:
                verify_media_launcher_token(bearer, _MEDIA_LAUNCHER_SECRET)
                return f(*args, **kwargs)
            except AuthError:
                logger.warning("Invalid media launcher token from %s", request.remote_addr)
                return jsonify({"ok": False, "err": "unauthorized"}), 401

        if ALLOW_LEGACY_AUTH and LEGACY_AUTH_TOKEN:
            legacy_header = request.headers.get("X-HUB-AUTH")
            if legacy_header and legacy_header == LEGACY_AUTH_TOKEN:
                logger.warning("Legacy media launcher auth used by %s", request.remote_addr)
                return f(*args, **kwargs)

        logger.warning("Unauthorized access attempt from %s", request.remote_addr)
        return jsonify({"ok": False, "err": "unauthorized"}), 401

    decorated_function.__name__ = f.__name__
    return decorated_function


# Global Flask app instance
app = Flask(__name__)

# Single-player model: last launched media process
_media_proc = None
_media_info = {}

# Global to store known PIDs (for zombie detection)
_known_pids = set()


# Load allowed domains from config file
def load_allowed_domains():
    """Load allowed domains from configuration file."""
    try:
        with open("config/media_whitelist.json", "r") as f:
            config = json.load(f)
            return config.get("allowed_domains", [])
    except FileNotFoundError:
        logger.warning("Config file config/media_whitelist.json not found, using default domains")
        # Return default list if config doesn't exist
        return [
            "youtube.com",
            "youtu.be",
            "twitch.tv",
            "pluto.tv",
            "roku.com",
            "roku.tv",
            "vimeo.com",
            "dailymotion.com",
            "tubitv.com",
            "spotify.com",
            "disneyplus.com",
            "max.com",
            "espn.com",
            "photos.google.com",
            "google.com",
            "therokuchannel.roku.com",
        ]
    except Exception as e:
        logger.error(f"Error loading whitelist config: {e}")
        # Return default list if there's an error
        return [
            "youtube.com",
            "youtu.be",
            "twitch.tv",
            "pluto.tv",
            "roku.com",
            "roku.tv",
            "vimeo.com",
            "dailymotion.com",
            "tubitv.com",
            "spotify.com",
            "disneyplus.com",
            "max.com",
            "espn.com",
            "photos.google.com",
            "google.com",
            "therokuchannel.roku.com",
        ]


def _get_launcher_port() -> int:
    endpoint = os.environ.get("MEDIA_LAUNCHER_ENDPOINT")
    if not endpoint:
        config_path = os.environ.get("CONFIG_PATH", "config.yaml")
        try:
            config = load_config(config_path)
            endpoint = getattr(getattr(config, "media", None), "launcher_endpoint", None)
        except Exception:
            endpoint = None
    if endpoint:
        parsed = urlparse(endpoint)
        if parsed.port:
            return parsed.port
    return 7666


ALLOWED_DOMAINS = load_allowed_domains()

# Set up logging
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/media_launcher.log"), logging.StreamHandler()],  # Also log to console
)
logger = logging.getLogger(__name__)


def _parse_media_url(raw_url):
    """Normalize and validate the media URL structure."""
    if not raw_url:
        return None
    url = raw_url.strip()
    if not url or len(url) > 2048:
        return None
    if any(ch.isspace() for ch in url):
        return None
    if any(ord(ch) < 32 for ch in url):
        return None
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    if parsed.scheme not in {"http", "https"}:
        return None
    if not parsed.netloc:
        return None
    if parsed.username or parsed.password:
        return None
    host = (parsed.hostname or "").lower().strip(".")
    if not host:
        return None
    sanitized_url = parsed._replace(fragment="").geturl()
    return sanitized_url, host


def _is_domain_allowed(host):
    for domain in ALLOWED_DOMAINS:
        normalized = str(domain).lower().strip(".")
        if host == normalized or host.endswith(f".{normalized}"):
            return True
    return False


def _parse_int_pair(value):
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        first = int(value[0])
        second = int(value[1])
    except (TypeError, ValueError):
        return None
    if first < 0 or second < 0 or first > 10000 or second > 10000:
        return None
    return [first, second]


def get_chrome_bin():
    if os.name == "nt":
        if os.path.exists(CHROME_WIN):
            return CHROME_WIN
        return "chrome"
    else:
        if os.path.exists(CHROME_LINUX):
            return CHROME_LINUX
        if shutil.which("chromium-browser"):
            return "chromium-browser"
        if shutil.which("chromium"):
            return "chromium"
        return "google-chrome"


def _launch_chrome_on_windows(url, position=None, size=None, controller=False):
    """Windows: spawn chrome with flags that create an app-like window."""
    chrome = get_chrome_bin()
    flags = [
        f"--app={url}",
        "--new-window",
        "--disable-infobars",
        "--noerrdialogs",
        "--disable-session-crashed-bubble",
        "--autoplay-policy=no-user-gesture-required",
        "--disable-extensions",
        "--disable-plugins",
    ]
    # Window position/size (optional)
    if position and size:
        flags += [f"--window-position={position[0]},{position[1]}", f"--window-size={size[0]},{size[1]}"]
    cmd = [chrome] + flags
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # nosec B603
        logger.info(f"Successfully launched Chrome process with PID: {proc.pid}")
        # If controller is requested, spawn a second window for the controller
        if controller:
            controller_proc = _launch_controller_on_windows(position=[8, 8], size=[120, 44])
            return [proc, controller_proc]  # Return both processes
        return proc
    except Exception as e:
        logger.error(f"Failed to launch Chrome process: {e}")
        raise


def _safe_terminate_process(proc):
    """Safely terminate a process with proper error handling."""
    if proc:
        try:
            terminated_pids = []
            if isinstance(proc, list):
                # Handle list of processes (media + controller)
                terminated_count = 0
                for p in proc:
                    if p and p.poll() is None:  # Check if process is still running
                        p.terminate()
                        terminated_count += 1
                        if hasattr(p, "pid"):
                            terminated_pids.append(p.pid)
                logger.info(f"Safely terminated {terminated_count} processes with PIDs: {terminated_pids}")
                # Remove these PIDs from known PIDs
                for pid in terminated_pids:
                    _known_pids.discard(pid)
                return True
            else:
                # Handle single process
                if proc.poll() is None:  # Check if process is still running
                    pid = proc.pid
                    proc.terminate()
                    logger.info(f"Safely terminated process PID: {pid}")
                    # Remove this PID from known PIDs
                    _known_pids.discard(pid)
                    return True
        except Exception as e:
            logger.error(f"Error terminating process: {e}")
            # If terminate fails, try kill as fallback
            try:
                killed_pids = []
                if isinstance(proc, list):
                    for p in proc:
                        if p and p.poll() is None:
                            if hasattr(p, "pid"):
                                killed_pids.append(p.pid)
                            p.kill()
                else:
                    if proc and proc.poll() is None:
                        if hasattr(proc, "pid"):
                            killed_pids.append(proc.pid)
                        proc.kill()
                logger.info(f"Force killed processes with PIDs: {killed_pids}")
                # Remove these PIDs from known PIDs
                for pid in killed_pids:
                    _known_pids.discard(pid)
            except Exception as e2:
                logger.error(f"Error force killing process: {e2}")
                return False
    return True


def _track_process_pid(proc):
    """Track a process PID for zombie cleanup purposes."""
    global _known_pids
    if isinstance(proc, list):
        for p in proc:
            if p and hasattr(p, "pid"):
                _known_pids.add(p.pid)
    else:
        if proc and hasattr(proc, "pid"):
            _known_pids.add(proc.pid)


def stale_pids_cleanup():
    """Detect and clean up zombie processes based on known PIDs."""
    global _known_pids
    cleaned_count = 0

    # Create a copy of the set to iterate over, since we'll be modifying it
    pids_to_check = _known_pids.copy()

    for pid in pids_to_check:
        try:
            # Try to get the process status - if this succeeds, process is still alive
            if psutil.pid_exists(pid):
                try:
                    proc = psutil.Process(pid)
                    # Check if it's one of our media processes by name/command line
                    proc_cmdline = " ".join(proc.cmdline()).lower()
                    if any(browser in proc_cmdline for browser in ["chrome", "chromium"]):
                        logger.info(f"Process PID {pid} is still running: {proc.name()}")
                        continue  # Skip cleaning this one
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    # Process might exist but we can't access it, or it's not a browser process
                    pass
            # If we get here, process either doesn't exist or is not a browser we control
            # Try to kill it just in case it's a zombie from our service
            try:
                os.kill(pid, 0)  # Check if process exists without killing it
                logger.info(f"Found potential zombie process with PID {pid}, attempting to kill it")
                os.kill(pid, signal.SIGTERM)  # Try graceful termination
                time.sleep(0.1)  # Brief wait
                # Check if it's still alive
                if psutil.pid_exists(pid):
                    if os.name == "nt":
                        psutil.Process(pid).kill()
                    else:
                        os.kill(pid, signal.SIGKILL)  # Force kill if still alive
                    logger.info(f"Force killed zombie process PID {pid}")
                else:
                    logger.info(f"Gracefully terminated zombie process PID {pid}")
                cleaned_count += 1
            except OSError:
                # Process doesn't exist anymore, which is fine
                pass
        except Exception as e:
            logger.error(f"Error checking/cleaning PID {pid}: {e}")

    # Clear the known pids set after cleanup
    _known_pids.clear()
    logger.info(f"Stale PID cleanup completed. Cleaned {cleaned_count} potential zombie processes")
    return cleaned_count


def _launch_chrome_on_linux(url, position=None, size=None, controller=False):
    chrome = get_chrome_bin()
    flags = [
        f"--app={url}",
        "--new-window",
        "--disable-infobars",
        "--noerrdialogs",
        "--disable-session-crashed-bubble",
        "--enable-features=VaapiVideoDecoder",  # Pi specific: test/optional
        "--use-gl=egl",
        "--autoplay-policy=no-user-gesture-required",
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ]
    if position and size:
        flags += [f"--window-position={position[0]},{position[1]}", f"--window-size={size[0]},{size[1]}"]
    cmd = [chrome] + flags
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # nosec B603
        logger.info(f"Successfully launched Chrome process with PID: {proc.pid}")
        # If controller is requested, spawn a second window for the controller
        if controller:
            controller_proc = _launch_controller_on_linux(position=[8, 8], size=[120, 44])
            return [proc, controller_proc]  # Return both processes
        return proc
    except Exception as e:
        logger.error(f"Failed to launch Chrome process: {e}")
        raise


def _launch_controller_on_windows(position=None, size=None):
    """Launch the media controller window on Windows."""
    chrome = get_chrome_bin()
    controller_url = "http://127.0.0.1:5000/media_control"
    flags = [
        f"--app={controller_url}",
        "--new-window",
        "--disable-infobars",
        "--noerrdialogs",
        "--disable-session-crashed-bubble",
        "--disable-extensions",
        "--disable-plugins",
    ]
    # Set position/size for the controller (small overlay window)
    if position and size:
        flags += [f"--window-position={position[0]},{position[1]}", f"--window-size={size[0]},{size[1]}"]
    else:
        # Default position and size if not specified
        flags += ["--window-position=8,8", "--window-size=120,44"]
    cmd = [chrome] + flags
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # nosec B603


def _launch_controller_on_linux(position=None, size=None):
    """Launch the media controller window on Linux."""
    chrome = get_chrome_bin()
    controller_url = "http://127.0.0.1:5000/media_control"
    flags = [
        f"--app={controller_url}",
        "--new-window",
        "--disable-infobars",
        "--noerrdialogs",
        "--disable-session-crashed-bubble",
        "--enable-features=VaapiVideoDecoder",  # Pi specific: test/optional
        "--use-gl=egl",
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ]
    # Set position/size for the controller (small overlay window)
    if position and size:
        flags += [f"--window-position={position[0]},{position[1]}", f"--window-size={size[0]},{size[1]}"]
    else:
        # Default position and size if not specified
        flags += ["--window-position=8,8", "--window-size=120,44"]
    cmd = [chrome] + flags
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # nosec B603


@app.route("/v1/open_media", methods=["POST"])
@require_auth
def open_media():
    global _media_proc, _media_info
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"ok": False, "err": "invalid-json"}), 400
    data = data or {}
    raw_url = data.get("url", "")
    if not isinstance(raw_url, str):
        return jsonify({"ok": False, "err": "invalid-url"}), 400
    if not raw_url.strip():
        return jsonify({"ok": False, "err": "missing-url"}), 400
    parsed = _parse_media_url(raw_url)
    if not parsed:
        return jsonify({"ok": False, "err": "invalid-url"}), 400
    url, host = parsed
    if not _is_domain_allowed(host):
        return jsonify({"ok": False, "err": "domain-not-allowed"}), 400

    # Optional: accept position/size for controller overlay layout
    pos = _parse_int_pair(data.get("position"))  # [x,y]
    size = _parse_int_pair(data.get("size"))  # [w,h]
    if data.get("position") is not None and pos is None:
        return jsonify({"ok": False, "err": "invalid-position"}), 400
    if data.get("size") is not None and size is None:
        return jsonify({"ok": False, "err": "invalid-size"}), 400
    controller = bool(data.get("controller", False))  # Whether to spawn controller window

    # Kill existing process if running (single-player)
    try:
        if _media_proc and _media_proc.poll() is None:
            # Use the safe termination function
            _safe_terminate_process(_media_proc)
            time.sleep(0.25)
            logger.info("Terminated existing media process(es)")
    except Exception as e:
        logger.error(f"Error terminating existing process: {e}")

    # Retry logic with backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if os.name == "nt":
                proc = _launch_chrome_on_windows(url, pos, size, controller)
            else:
                proc = _launch_chrome_on_linux(url, pos, size, controller)

            _media_proc = proc
            # Track the process PID(s) for potential cleanup
            _track_process_pid(proc)

            # Handle both single process and list of processes
            if isinstance(proc, list):
                # Media + controller processes
                media_pid = proc[0].pid if proc[0] else None
                controller_pid = proc[1].pid if proc[1] else None
                _media_info = {"url": url, "pid": media_pid, "controller_pid": controller_pid, "ts": time.time()}
                logger.info(f"Launched media window for {url}, PID: {media_pid}, Controller PID: {controller_pid}")
                return jsonify({"ok": True, "pid": media_pid, "controller_pid": controller_pid, "url": url})
            else:
                # Single media process only
                _media_info = {"url": url, "pid": proc.pid if proc else None, "ts": time.time()}
                logger.info(f"Launched media window for {url}, PID: {_media_info['pid']}")
                return jsonify({"ok": True, "pid": _media_info["pid"], "url": url})
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} to launch media failed: {e}")
            if attempt < max_retries - 1:
                # Backoff: wait longer between attempts
                time.sleep(0.5 * (attempt + 1))
                continue
            else:
                # All retries failed
                logger.error(f"Failed to launch media after {max_retries} attempts: {e}")
                return jsonify({"ok": False, "err": f"launch-failed-after-{max_retries}-retries"}), 500

    # This line should not be reached if the loop works correctly
    return jsonify({"ok": False, "err": "unknown-error"}), 500


@app.route("/v1/close_media", methods=["POST"])
@require_auth
def close_media():
    global _media_proc, _media_info
    if _media_proc:
        # Use the safe termination function
        success = _safe_terminate_process(_media_proc)
        if success:
            _media_proc = None  # Clear the reference
            _media_info = {}  # Clear the info
            logger.info("Successfully closed media process(es)")
            return jsonify({"ok": True})
        else:
            logger.error("Failed to close media process(es)")
            return jsonify({"ok": False, "err": "failed-to-terminate-process"}), 500
    logger.info("No media process running to close")
    return jsonify({"ok": False, "err": "no-media-running"}), 404


@app.route("/v1/media_status", methods=["GET"])
@require_auth
def media_status():
    """Get the status of the current media window"""
    global _media_proc, _media_info
    if _media_proc:
        if isinstance(_media_proc, list):
            # Check if both media and controller processes are still running
            media_running = _media_proc[0] and (_media_proc[0].poll() is None if _media_proc[0] else False)
            controller_running = _media_proc[1] and (_media_proc[1].poll() is None if _media_proc[1] else False)
            is_running = media_running or controller_running

            # Build status response
            status = {
                "ok": True,
                "active": is_running,
                "media_running": media_running,
                "controller_running": controller_running,
                "pid": _media_proc[0].pid if _media_proc[0] and media_running else None,
                "controller_pid": _media_proc[1].pid if _media_proc[1] and controller_running else None,
                "url": _media_info.get("url", ""),
                "timestamp": _media_info.get("ts", 0),
            }
            return jsonify(status)
        else:
            # Single process case
            is_running = _media_proc.poll() is None
            status = {
                "ok": True,
                "active": is_running,
                "media_running": is_running,
                "controller_running": False,
                "pid": _media_proc.pid if _media_proc and is_running else None,
                "controller_pid": None,
                "url": _media_info.get("url", ""),
                "timestamp": _media_info.get("ts", 0),
            }
            return jsonify(status)
    else:
        # No media process running
        status = {
            "ok": True,
            "active": False,
            "media_running": False,
            "controller_running": False,
            "pid": None,
            "controller_pid": None,
            "url": "",
            "timestamp": 0,
        }
        return jsonify(status)


@app.route("/health", methods=["GET"])
def health():
    """Basic health check endpoint - does not require auth to allow monitoring tools to check status"""
    is_running = _media_proc and _media_proc.poll() is None
    return jsonify({"ok": True, "media_running": is_running})


def cleanup():
    """Clean up any running processes when the service exits"""
    global _media_proc
    if _media_proc:
        try:
            if isinstance(_media_proc, list):
                # Handle list of processes (media + controller)
                for proc in _media_proc:
                    if proc and proc.poll() is None:
                        logger.info(f"Shutting down: terminating media process PID: {proc.pid}")
                        proc.terminate()
                        # Wait a bit for graceful shutdown
                        try:
                            proc.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            # Force kill if it doesn't terminate gracefully
                            proc.kill()
            else:
                # Handle single process
                if _media_proc and _media_proc.poll() is None:
                    logger.info(f"Shutting down: terminating media process PID: {_media_proc.pid}")
                    _media_proc.terminate()
                    # Wait a bit for graceful shutdown
                    try:
                        _media_proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        # Force kill if it doesn't terminate gracefully
                        _media_proc.kill()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Register cleanup function to run on exit
atexit.register(cleanup)


# Handle SIGTERM signals gracefully
def signal_handler(sig, frame):
    logger.info("Received SIGTERM, shutting down gracefully...")
    cleanup()
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)


def startup_routine():
    """Run startup tasks like zombie cleanup."""
    logger.info("Running startup routine...")
    # Clean up any stale PIDs from previous runs
    stale_pids_cleanup()
    logger.info("Startup routine completed")


def run_media_launcher_service():
    """Function to run the media launcher service as a standalone service"""
    # Run startup routine at start
    startup_routine()
    app.run(host="127.0.0.1", port=_get_launcher_port(), debug=False)


class MediaLauncherService:
    """Lightweight wrapper for managing media window processes."""

    def __init__(self):
        self.media_processes = []

    def spawn_media_window(self, url, position=None, size=None, controller=False):
        parsed = _parse_media_url(url)
        if not parsed:
            raise ValueError("invalid-url")
        sanitized_url, host = parsed
        if not _is_domain_allowed(host):
            raise ValueError("domain-not-allowed")

        pos = _parse_int_pair(position)
        size = _parse_int_pair(size)
        if position is not None and pos is None:
            raise ValueError("invalid-position")
        if size is not None and size is None:
            raise ValueError("invalid-size")

        if os.name == "nt":
            proc = _launch_chrome_on_windows(sanitized_url, pos, size, controller)
        else:
            proc = _launch_chrome_on_linux(sanitized_url, pos, size, controller)

        self._track_process(proc)
        return proc

    def kill_media_window(self, proc):
        if proc is None:
            return False
        success = _safe_terminate_process(proc)
        if success:
            self._remove_process(proc)
        return success

    def kill_all_media_windows(self):
        for proc in list(self.media_processes):
            self.kill_media_window(proc)
        return True

    def get_active_windows(self):
        active = []
        for proc in self.media_processes:
            if isinstance(proc, list):
                if any(p and p.poll() is None for p in proc):
                    active.append(proc)
            elif proc and proc.poll() is None:
                active.append(proc)
        return active

    def _find_chrome_windows(self):
        return self.get_active_windows()

    def _track_process(self, proc):
        self.media_processes.append(proc)

    def _remove_process(self, proc):
        try:
            self.media_processes.remove(proc)
        except ValueError:
            pass


if __name__ == "__main__":
    run_media_launcher_service()
