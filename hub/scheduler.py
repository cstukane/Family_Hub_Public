import atexit
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

from hub.db import get_db
from hub.services import calendar, weather


def _get_section(config, name):
    """Return config section regardless of dict/model representation."""
    if hasattr(config, name):
        return getattr(config, name)
    if isinstance(config, dict):
        return config.get(name)
    return None


def _get_flag(section, attr, default=False):
    """Read a boolean flag from a config section."""
    if section is None:
        return default
    if hasattr(section, attr):
        value = getattr(section, attr)
    elif isinstance(section, dict):
        value = section.get(attr, default)
    else:
        value = default
    return default if value is None else value


def create_scheduler(app: Flask):
    """Create and configure the background scheduler with jobs."""
    scheduler = BackgroundScheduler()
    config = app.config.get("CONFIG")
    features_cfg = _get_section(config, "features")
    services_cfg = _get_section(config, "services")
    casting_cfg = _get_section(config, "casting")

    # Add scheduled jobs
    scheduler.add_job(
        func=lambda: refresh_weather_data(app),
        trigger="interval",
        minutes=15,  # Every 15 minutes
        id="weather_refresh",
        name="Refresh weather data every 15 minutes",
        replace_existing=True,
    )

    scheduler.add_job(
        func=lambda: refresh_calendar_data(app),
        trigger="interval",
        minutes=15,  # Every 15 minutes for ICS calendar
        id="calendar_refresh",
        name="Refresh calendar data every 15 minutes",
        replace_existing=True,
    )

    # Add scheduled job for sports ticker data refresh (fixed interval implementation for now)
    if _get_flag(features_cfg, "sports_ticker_enabled", True):
        scheduler.add_job(
            func=lambda: refresh_sports_ticker_data_adaptive(app),
            trigger="interval",
            seconds=300,  # Fixed 5-minute interval as a fallback implementation
            id="sports_ticker_refresh",
            name="Refresh sports ticker data",
            replace_existing=True,
        )

    # Add cache cleanup job (daily)
    scheduler.add_job(
        func=lambda: cleanup_expired_cache(app),
        trigger="interval",
        hours=24,
        id="cache_cleanup",
        name="Clean up expired cache entries daily",
        replace_existing=True,
    )

    # Optional attic jobs are registered only after an explicit opt-in.
    if _get_flag(services_cfg, "update_checks", False):
        scheduler.add_job(
            func=lambda: check_for_updates_and_notify(app),
            trigger="interval",
            hours=24,  # Daily check
            id="update_check",
            name="Check for application updates daily",
            replace_existing=True,
        )

    # Add weather alert monitoring job (runs every 30 minutes)
    if _get_flag(services_cfg, "weather_alerts", False):
        scheduler.add_job(
            func=lambda: monitor_weather_alerts(app),
            trigger="interval",
            minutes=30,  # Every 30 minutes
            id="weather_alert_monitor",
            name="Monitor weather alerts",
            replace_existing=True,
        )

    # Webhook monitoring is dormant unless the service and at least one destination are enabled.
    webhooks_cfg = _get_section(config, "webhooks") or []
    active_webhooks = any(_get_flag(item, "active", False) for item in webhooks_cfg)
    if _get_flag(services_cfg, "webhooks", False) and active_webhooks:
        scheduler.add_job(
            func=lambda: check_webhook_statuses(app),
            trigger="interval",
            minutes=15,
            id="webhook_status_check",
            name="Check webhook statuses",
            replace_existing=True,
        )

    # Add casting device discovery job (if casting is enabled)
    casting_enabled = _get_flag(casting_cfg, "enabled", False)
    discovery_enabled = _get_flag(casting_cfg, "discovery_enabled", False)
    if casting_enabled and discovery_enabled:
        scheduler.add_job(
            func=lambda: discover_casting_devices(app),
            trigger="interval",
            seconds=300,  # Every 5 minutes
            id="casting_device_discovery",
            name="Discover casting devices",
            replace_existing=True,
        )

    if not app.config.get("TESTING"):
        scheduler.start()
        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())

    return scheduler


def refresh_weather_data(app: Flask) -> None:
    """Refresh weather data from the provider and cache it."""
    with app.app_context():
        try:
            # Clear weather cache first to ensure fresh data is fetched
            from hub.cache import clear_weather_cache

            cleared_count = clear_weather_cache()
            if cleared_count > 0:
                app.logger.info(f"Refreshed weather data: cleared {cleared_count} weather cache entries")
            else:
                app.logger.info("Refreshed weather data: no weather cache entries to clear")

            # Get weather data which will trigger fresh API calls and cache updates in the service
            weather.get_weather_data(force_refresh=True)

            # Log the refresh
            db = get_db()
            db.execute(
                """INSERT INTO audit (actor, action, payload)
                   VALUES (?, ?, ?)""",
                (
                    "scheduler",
                    "weather_refresh",
                    f"Weather data refreshed at {datetime.now().isoformat()}: Current weather updated",
                ),
            )
            db.commit()
        except Exception as e:
            app.logger.error(f"Error refreshing weather data: {e}")


def refresh_calendar_data(app: Flask) -> None:
    """Refresh calendar data from ICS provider and cache it."""
    with app.app_context():
        try:
            # Call calendar service which will handle caching
            from datetime import datetime, timedelta

            now = datetime.now()
            future = now + timedelta(days=30)  # Get next 30 days of events
            calendar.list_events(now, future)

            # Log the refresh
            db = get_db()
            db.execute(
                """INSERT INTO audit (actor, action, payload)
                   VALUES (?, ?, ?)""",
                ("scheduler", "calendar_refresh", f"Calendar data refreshed at {datetime.now().isoformat()}"),
            )
            db.commit()
        except Exception as e:
            app.logger.error(f"Error refreshing calendar data: {e}")


def refresh_sports_ticker_data_adaptive(app: Flask) -> None:
    """Refresh sports ticker data and reschedule at an adaptive interval based on live game state."""
    with app.app_context():
        try:
            config = app.config.get("CONFIG")
            features_cfg = _get_section(config, "features")
            if not _get_flag(features_cfg, "sports_ticker_enabled", True):
                app.logger.info("Sports ticker disabled; skipping refresh job.")
                return

            from hub.services.sports_ticker_service import get_polling_interval, get_sports_ticker_data

            # Read favorite_teams and polling_defaults from config
            sports_cfg = _get_section(config, "providers") or {}
            if hasattr(sports_cfg, "get"):
                sports_provider = sports_cfg.get("sports", {})
            else:
                sports_provider = getattr(sports_cfg, "sports", {}) or {}
            if hasattr(sports_provider, "get"):
                favorite_teams = list(sports_provider.get("favorite_teams", []) or [])
            else:
                favorite_teams = list(getattr(sports_provider, "favorite_teams", []) or [])

            polling_defaults = {"active": 90, "idle": 300, "post_final": 150, "no_games": 1800}

            # Fetch fresh data and capture the returned dict
            result = get_sports_ticker_data(favorite_teams, force_refresh=True)
            games = result.get("games", []) if result else []

            # Compute adaptive interval and clamp between 60s and 1800s
            interval = get_polling_interval(games, favorite_teams, polling_defaults)
            interval = max(60, min(1800, interval))

            # Reschedule the job with the new interval
            try:
                app.scheduler.reschedule_job("sports_ticker_refresh", trigger="interval", seconds=interval)
                app.logger.info(f"Sports ticker rescheduled: next poll in {interval}s ({len(games)} games visible)")
            except Exception as reschedule_exc:
                app.logger.warning(f"Could not reschedule sports ticker job: {reschedule_exc}")

            # Audit log
            db = get_db()
            db.execute(
                """INSERT INTO audit (actor, action, payload)
                   VALUES (?, ?, ?)""",
                (
                    "scheduler",
                    "sports_ticker_refresh",
                    f"Sports ticker refreshed at {datetime.now().isoformat()}, next in {interval}s",
                ),
            )
            db.commit()

        except Exception as e:
            app.logger.error(f"Error refreshing sports ticker data: {e}")


def refresh_sports_ticker_data(app: Flask) -> None:
    """Refresh sports ticker data specifically."""
    with app.app_context():
        try:
            config = app.config.get("CONFIG")
            features_cfg = _get_section(config, "features")
            if not _get_flag(features_cfg, "sports_ticker_enabled", True):
                app.logger.info("Sports ticker disabled; skipping manual refresh.")
                return
            # Call sports ticker service to refresh data
            from hub.services.sports_ticker_service import refresh_sports_ticker_data as ticker_refresh

            success = ticker_refresh()

            if success:
                # Log the refresh
                db = get_db()
                db.execute(
                    """INSERT INTO audit (actor, action, payload)
                       VALUES (?, ?, ?)""",
                    (
                        "scheduler",
                        "sports_ticker_refresh",
                        f"Sports ticker data refreshed at {datetime.now().isoformat()}",
                    ),
                )
                db.commit()
            else:
                app.logger.error("Failed to refresh sports ticker data")
        except Exception as e:
            app.logger.error(f"Error refreshing sports ticker data: {e}")


def cleanup_expired_cache(app: Flask) -> None:
    """Clean up expired cache entries."""
    with app.app_context():
        try:
            from hub.cache import cleanup_expired

            removed_count = cleanup_expired()

            # Log the cleanup
            db = get_db()
            db.execute(
                """INSERT INTO audit (actor, action, payload)
                   VALUES (?, ?, ?)""",
                (
                    "scheduler",
                    "cache_cleanup",
                    f"Cleaned up {removed_count} expired cache entries at {datetime.now().isoformat()}",
                ),
            )
            db.commit()
        except Exception as e:
            app.logger.error(f"Error cleaning up cache: {e}")


def check_for_updates_and_notify(app: Flask) -> None:
    """Check for updates and notify if available."""
    with app.app_context():
        try:
            from hub.services import check_for_updates

            # Check for updates
            updates_result = check_for_updates()

            if updates_result.get("has_updates"):
                # Log that updates are available
                db = get_db()
                db.execute(
                    """INSERT INTO audit (actor, action, payload)
                       VALUES (?, ?, ?)""",
                    (
                        "scheduler",
                        "update_available",
                        f"Updates available: {updates_result.get('updates', [])} at {datetime.now().isoformat()}",
                    ),
                )
                db.commit()

                app.logger.info(f"Updates available: {updates_result.get('updates')}")
            else:
                app.logger.info("No updates available")
        except Exception as e:
            app.logger.error(f"Error checking for updates: {e}")


def monitor_weather_alerts(app: Flask) -> None:
    """Monitor weather alerts and trigger webhooks if thresholds are exceeded."""
    with app.app_context():
        try:
            config = app.config.get("CONFIG")
            services_cfg = _get_section(config, "services")
            if not _get_flag(services_cfg, "weather_alerts", True):
                app.logger.info("Weather alerts disabled; skipping monitor job.")
                return
            from hub.services import weather_alert

            # Process weather alerts which will trigger webhooks if thresholds are exceeded
            result = weather_alert.process_weather_alerts()

            # Log the result
            db = get_db()
            db.execute(
                """INSERT INTO audit (actor, action, payload)
                   VALUES (?, ?, ?)""",
                (
                    "scheduler",
                    "weather_alert_monitor",
                    f"Weather alert check result: {result} at {datetime.now().isoformat()}",
                ),
            )
            db.commit()

            app.logger.info(f"Weather alert monitoring completed: {result.get('message', 'Unknown status')}")
        except Exception as e:
            app.logger.error(f"Error in weather alert monitoring: {e}")


def check_webhook_statuses(app: Flask) -> None:
    """Check webhook statuses."""
    with app.app_context():
        try:
            from hub.services import get_all_webhooks

            webhooks = get_all_webhooks()

            # Log the webhook status check
            db = get_db()
            db.execute(
                """INSERT INTO audit (actor, action, payload)
                   VALUES (?, ?, ?)""",
                (
                    "scheduler",
                    "webhook_status_check",
                    f"Checked {len(webhooks)} webhooks at {datetime.now().isoformat()}",
                ),
            )
            db.commit()

            app.logger.info(f"Webhook status check completed: {len(webhooks)} webhooks configured")
        except Exception as e:
            app.logger.error(f"Error in webhook status check: {e}")


def discover_casting_devices(app: Flask) -> None:
    """Discover casting devices on the network."""
    with app.app_context():
        try:
            from hub.services import casting_manager

            config = app.config.get("CONFIG")
            if not config or not hasattr(config, "casting") or not config.casting.enabled:
                app.logger.info("Casting not enabled, skipping device discovery")
                return

            success = casting_manager.refresh_device_list()

            if success:
                # Log the discovery
                db = get_db()
                db.execute(
                    """INSERT INTO audit (actor, action, payload)
                       VALUES (?, ?, ?)""",
                    (
                        "scheduler",
                        "casting_device_discovery",
                        f"Casting devices refreshed at {datetime.now().isoformat()}",
                    ),
                )
                db.commit()

                app.logger.info("Casting device discovery completed successfully")
            else:
                app.logger.error("Casting device discovery failed")
        except Exception as e:
            app.logger.error(f"Error in casting device discovery: {e}")
