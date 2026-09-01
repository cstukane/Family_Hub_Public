import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS casting_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            device_id TEXT UNIQUE,
            device_type TEXT NOT NULL,  -- google_cast, roku, alexa, etc.
            ip_address TEXT,
            port INTEGER,
            friendly_name TEXT,
            is_active INTEGER DEFAULT 1,
            last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS media_queues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            queue_items TEXT,  -- JSON array of queue items
            current_item_index INTEGER DEFAULT 0,
            is_playing INTEGER DEFAULT 0,
            volume INTEGER DEFAULT 50,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES casting_devices (device_id)
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS casting_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            devices TEXT NOT NULL,  -- JSON array of device IDs
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
