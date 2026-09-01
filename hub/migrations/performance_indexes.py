import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute("CREATE INDEX IF NOT EXISTS idx_events_local_starts_at ON events_local(starts_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_events_local_calendar_id ON events_local(calendar_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_chores_completed_due_date ON chores(completed, due_date)")
