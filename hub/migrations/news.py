import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS news_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )

    db.execute("CREATE INDEX IF NOT EXISTS idx_news_preferences_category ON news_preferences(category)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_news_preferences_enabled ON news_preferences(enabled)")
