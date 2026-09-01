import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS music_tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            album TEXT,
            genre TEXT,
            duration INTEGER, -- in seconds
            source TEXT DEFAULT 'local',
            album_art_url TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS playlist_tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER NOT NULL,
            track_id INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (playlist_id) REFERENCES playlists (id) ON DELETE CASCADE,
            FOREIGN KEY (track_id) REFERENCES music_tracks (id) ON DELETE CASCADE,
            UNIQUE(playlist_id, track_id)
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS music_queues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER,
            queue_items TEXT,  -- JSON array of queue items
            current_item_index INTEGER DEFAULT 0,
            is_playing INTEGER DEFAULT 0,
            volume INTEGER DEFAULT 50,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (playlist_id) REFERENCES playlists (id) ON DELETE SET NULL
        )"""
    )

    db.execute("CREATE INDEX IF NOT EXISTS idx_music_tracks_artist ON music_tracks(artist)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_music_tracks_album ON music_tracks(album)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_music_tracks_genre ON music_tracks(genre)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_playlists_name ON playlists(name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist ON playlist_tracks(playlist_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_playlist_tracks_track ON playlist_tracks(track_id)")
