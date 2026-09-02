import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS events_local (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            starts_at TIMESTAMP,
            ends_at TIMESTAMP,
            location TEXT,
            source TEXT DEFAULT 'local',
            description TEXT,
            all_day INTEGER DEFAULT 0,
            visibility TEXT,
            color TEXT,
            calendar_id TEXT,
            guests TEXT,
            reminders TEXT
        )"""
    )

    existing_columns = {row["name"] for row in db.execute("PRAGMA table_info(events_local)").fetchall()}
    column_defaults = {
        "description": "TEXT",
        "all_day": "INTEGER DEFAULT 0",
        "visibility": "TEXT",
        "color": "TEXT",
        "calendar_id": "TEXT",
        "guests": "TEXT",
        "reminders": "TEXT",
    }
    for column_name, column_type in column_defaults.items():
        if column_name not in existing_columns:
            db.execute(f"ALTER TABLE events_local ADD COLUMN {column_name} {column_type}")
