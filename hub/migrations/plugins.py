import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS plugins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            version TEXT NOT NULL,
            author TEXT,
            description TEXT,
            type TEXT,  -- service, adapter, ui, integration, custom
            status TEXT DEFAULT 'installed',  -- installed, enabled, disabled, broken
            enabled INTEGER DEFAULT 1,  -- 1 for enabled, 0 for disabled
            installed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS plugin_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plugin_name TEXT NOT NULL,
            setting_key TEXT NOT NULL,
            setting_value TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plugin_name) REFERENCES plugins (name) ON DELETE CASCADE
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS plugin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plugin_name TEXT NOT NULL,
            level TEXT NOT NULL,  -- info, warning, error, debug
            message TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plugin_name) REFERENCES plugins (name) ON DELETE CASCADE
        )"""
    )

    db.execute("CREATE INDEX IF NOT EXISTS idx_plugins_name ON plugins(name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_plugins_status ON plugins(status)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_plugins_enabled ON plugins(enabled)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_plugin_settings_plugin ON plugin_settings(plugin_name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_plugin_logs_plugin ON plugin_logs(plugin_name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_plugin_logs_timestamp ON plugin_logs(timestamp)")
