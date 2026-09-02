import sqlite3


def _has_column(db: sqlite3.Connection, table: str, column: str) -> bool:
    cursor = db.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def apply(db: sqlite3.Connection) -> None:
    if not _has_column(db, "cache", "last_accessed"):
        db.execute("ALTER TABLE cache ADD COLUMN last_accessed TIMESTAMP")
        db.execute("UPDATE cache SET last_accessed = updated_at WHERE last_accessed IS NULL")
    db.execute("CREATE INDEX IF NOT EXISTS idx_cache_last_accessed ON cache(last_accessed)")
