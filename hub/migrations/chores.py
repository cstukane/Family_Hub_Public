import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS chores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            assignee TEXT,
            due_date TIMESTAMP,
            completed INTEGER DEFAULT 0,
            recurring_schedule TEXT,  -- daily, weekly, monthly, etc.
            priority TEXT DEFAULT 'normal',  -- low, normal, high, urgent
            description TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )"""
    )

    db.execute("CREATE INDEX IF NOT EXISTS idx_chores_assignee ON chores(assignee)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_chores_due_date ON chores(due_date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_chores_completed ON chores(completed)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_chores_priority ON chores(priority)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_chores_created ON chores(created_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_chores_updated ON chores(updated_at)")
