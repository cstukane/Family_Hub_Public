import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            text TEXT NOT NULL
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS shopping_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            text TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            qty TEXT
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS timers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT,
            ends_at TIMESTAMP,
            active INTEGER
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ttl_seconds INTEGER
        )"""
    )

    db.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_shopping_done ON shopping_items(done)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_timers_ends ON timers(ends_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON cache(key)")
