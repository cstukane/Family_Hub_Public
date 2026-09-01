import os
import shutil
import sqlite3
from datetime import datetime
from typing import Any, Optional

import click
from flask import Flask, current_app, g
from flask.cli import with_appcontext


# Custom timestamp converter to handle ISO format timestamps
def convert_timestamp(val):
    """Convert timestamp from SQLite to datetime object."""
    if val is None:
        return None
    if isinstance(val, bytes):
        val = val.decode("utf-8")
    try:
        # Try to parse as ISO format with 'T'
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except ValueError:
        # If it fails, return None or current datetime as fallback
        return datetime.now()


# Register the custom converter
sqlite3.register_converter("timestamp", convert_timestamp)


def get_db() -> sqlite3.Connection:
    """Get database connection, creating one if it doesn't exist."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e: Optional[Any] = None) -> None:  # noqa: ANN401, ARG001
    """Close the database connection if it exists."""
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db() -> None:
    """Initialize the database with tables."""
    db = get_db()
    from hub.migrations import MIGRATIONS

    _ensure_migrations_table(db)
    applied = _get_applied_migrations(db)

    for name, migration in MIGRATIONS:
        if name in applied:
            continue
        migration(db)
        db.execute(
            "INSERT INTO schema_migrations (name, applied_at) VALUES (?, datetime('now'))",
            (name,),
        )

    db.commit()


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    """Clear the existing data and create new tables."""
    init_db()
    click.echo("Initialized the database.")


@click.command("backup-db")
@with_appcontext
def backup_db_command() -> None:
    """Create a database-only backup."""
    backup_path = backup_db()
    click.echo(f"Database backup created: {backup_path}")


def init_app(app: Flask) -> None:
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(backup_db_command)


def init_admin_account(app: Flask) -> None:
    """Initialize admin account if it doesn't exist."""
    import os

    with app.app_context():
        config = app.config.get("CONFIG")
        if not config or not config.security.admin_enabled:
            return  # Admin not enabled, don't create account

        # Check if we have admin credentials in the config
        if config.security.admin_username and config.security.admin_password_hash:
            app.logger.info("Admin account already configured")
            return

        # Set up admin credentials from environment variables only - no defaults
        admin_username = os.environ.get("ADMIN_USERNAME")
        admin_password = os.environ.get("ADMIN_PASSWORD")

        if admin_username and admin_password:
            from hub.services import hash_password

            hashed_password = hash_password(admin_password)

            # Update the config in memory and save to file
            config_path = app.config.get("CONFIG_PATH", "config.yaml")
            import yaml

            # Load current config
            with open(config_path, encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)

            # Update security section with admin credentials
            if "security" not in raw_config:
                raw_config["security"] = {}

            raw_config["security"]["admin_username"] = admin_username
            raw_config["security"]["admin_password_hash"] = hashed_password
            raw_config["security"]["admin_enabled"] = True

            # Write updated config back to file
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(raw_config, f, default_flow_style=False)

            app.logger.info(f"Admin account created: {admin_username}")

            # Update the config in the app
            from hub.config import load_config

            app.config["CONFIG"] = load_config(config_path)
        else:
            # If admin is enabled but no credentials are provided, raise an error
            # to prevent insecure default credentials from being written to config
            if config.security.admin_enabled:
                error_msg = (
                    "Admin panel is enabled but no ADMIN_USERNAME and ADMIN_PASSWORD environment "
                    "variables are set. Please set these variables to secure credentials to "
                    "prevent default insecure credentials from being used."
                )
                app.logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                app.logger.info("Admin account not created - disabled in config")


def _ensure_migrations_table(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )


def _get_applied_migrations(db: sqlite3.Connection) -> set:
    rows = db.execute("SELECT name FROM schema_migrations").fetchall()
    return {row[0] for row in rows}


def backup_db(backup_dir: Optional[str] = None) -> str:
    """Create a timestamped database backup and return the path."""
    db_path = current_app.config.get("DATABASE")
    if not db_path:
        raise ValueError("DATABASE path is not configured")

    if backup_dir is None:
        backup_dir = os.path.join(current_app.instance_path, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"family_hub.db.{timestamp}.bak")
    shutil.copy2(db_path, backup_path)
    current_app.logger.info("Database backup created: %s", backup_path)
    return backup_path
