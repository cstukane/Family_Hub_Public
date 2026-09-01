import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            event_types TEXT NOT NULL, -- JSON array of event types
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            secret TEXT, -- Optional secret for signing payloads
            headers TEXT -- JSON object of custom headers
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS webhook_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            webhook_id INTEGER NOT NULL,
            payload TEXT NOT NULL, -- JSON payload sent
            status TEXT NOT NULL, -- success, error, timeout
            response TEXT, -- Response from webhook endpoint
            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (webhook_id) REFERENCES webhooks (id)
        )"""
    )

    db.execute("CREATE INDEX IF NOT EXISTS idx_webhooks_active ON webhooks(active)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_webhook_logs_webhook_id ON webhook_logs(webhook_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_webhook_logs_timestamp ON webhook_logs(timestamp)")
