import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actor TEXT,
            action TEXT,
            payload TEXT
        )"""
    )
