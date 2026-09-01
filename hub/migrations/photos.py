import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            title TEXT,
            description TEXT,
            date_taken TIMESTAMP,
            source TEXT DEFAULT 'local',
            tags TEXT DEFAULT '[]',  -- JSON array of tags
            album_id INTEGER,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (album_id) REFERENCES albums (id)
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS albums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )

    db.execute("CREATE INDEX IF NOT EXISTS idx_photos_album ON photos(album_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photos_source ON photos(source)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_photos_date_taken ON photos(date_taken)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_albums_name ON albums(name)")
