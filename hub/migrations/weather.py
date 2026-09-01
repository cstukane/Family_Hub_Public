import sqlite3


def apply(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS weather_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            location TEXT,
            description TEXT,
            current_value REAL,
            threshold_value REAL,
            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )

    db.execute("CREATE INDEX IF NOT EXISTS idx_weather_alerts_timestamp ON weather_alerts(timestamp)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_weather_alerts_type ON weather_alerts(alert_type)")
