import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            ingredients TEXT,  -- JSON string
            steps TEXT,        -- JSON string
            prep_time INTEGER DEFAULT 0,
            cook_time INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )

    db.execute("CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title)")
