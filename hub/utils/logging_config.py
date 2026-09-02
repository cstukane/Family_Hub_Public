import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


def _env_truthy(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: Optional[str], default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def configure_logging(app=None) -> None:
    """Configure root logging for console + rotating file output."""
    if getattr(configure_logging, "_configured", False):
        return

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    log_format = os.environ.get(
        "LOG_FORMAT",
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    date_format = os.environ.get("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
    log_console = _env_truthy(os.environ.get("LOG_CONSOLE", "true"))
    log_file = os.environ.get("LOG_FILE")
    if not log_file and app:
        log_file = app.config.get("LOG_FILE")
        if not log_file:
            app_config = app.config.get("CONFIG")
            if app_config is not None:
                logging_config = getattr(app_config, "logging", None)
                log_file = (
                    getattr(app_config, "log_file", None)
                    or getattr(logging_config, "log_file", None)
                    or getattr(logging_config, "file_path", None)
                )

    if not log_file:
        base_dir = app.instance_path if app is not None else ""
        log_file = os.path.join(base_dir, "logs", "family_hub.log")
    max_bytes = _parse_int(os.environ.get("LOG_MAX_BYTES"), 10 * 1024 * 1024)
    backup_count = _parse_int(os.environ.get("LOG_BACKUP_COUNT"), 5)

    formatter = logging.Formatter(log_format, datefmt=date_format)
    handlers = []

    if log_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    if log_file:
        try:
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except OSError:
            # If file logging fails, continue with console-only output.
            pass

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = handlers or [logging.StreamHandler()]
    for handler in root.handlers:
        if handler.formatter is None:
            handler.setFormatter(formatter)

    if app is not None:
        app.logger.handlers = []
        app.logger.propagate = True
        app.logger.setLevel(level)

    configure_logging._configured = True
