import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS iot_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            device_type TEXT NOT NULL,  -- alexa, google_home, etc.
            device_id TEXT,
            host TEXT,
            port INTEGER,
            is_active INTEGER DEFAULT 1,
            config TEXT,  -- JSON configuration
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )

    db.execute("CREATE INDEX IF NOT EXISTS idx_iot_devices_type ON iot_devices(device_type)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_iot_devices_active ON iot_devices(is_active)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_iot_devices_host ON iot_devices(host)")
