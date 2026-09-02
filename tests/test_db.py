import os
import sqlite3
import tempfile

from hub.db import init_db


def test_database_init(app):
    """Test that database initialization works correctly."""
    with app.app_context():
        # Initialize the database
        init_db()

        # Connect to the database
        db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row

        # Test that the notes table exists and is empty
        result = db.execute("SELECT * FROM notes").fetchall()
        assert len(result) == 0

        # Test that the shopping_items table exists and is empty
        result = db.execute("SELECT * FROM shopping_items").fetchall()
        assert len(result) == 0

        # Test that the events_local table exists and is empty
        result = db.execute("SELECT * FROM events_local").fetchall()
        assert len(result) == 0

        # Test that expected tables exist
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [table[0] for table in tables]
        expected_tables = ["notes", "shopping_items", "timers", "cache", "events_local", "audit"]
        for expected_table in expected_tables:
            assert expected_table in table_names

        db.close()


def test_notes_table_structure(app):
    """Test the structure of the notes table."""
    with app.app_context():
        init_db()

        db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row

        # Insert a test note
        db.execute("INSERT INTO notes (text) VALUES (?)", ("Test note",))
        db.commit()

        # Retrieve the note
        result = db.execute("SELECT * FROM notes WHERE text = ?", ("Test note",)).fetchone()
        assert result is not None
        assert result["text"] == "Test note"

        db.close()


def test_shopping_items_table_structure(app):
    """Test the structure of the shopping_items table."""
    with app.app_context():
        init_db()

        db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row

        # Insert a test shopping item
        db.execute("INSERT INTO shopping_items (text, qty, done) VALUES (?, ?, ?)", ("Milk", "1 gallon", 0))
        db.commit()

        # Retrieve the item
        result = db.execute("SELECT * FROM shopping_items WHERE text = ?", ("Milk",)).fetchone()
        assert result is not None
        assert result["text"] == "Milk"
        assert result["qty"] == "1 gallon"
        assert result["done"] == 0

        db.close()


def test_events_local_table_structure(app):
    """Test the structure of the events_local table."""
    with app.app_context():
        init_db()

        db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row

        # Insert a test event
        db.execute(
            "INSERT INTO events_local (title, starts_at, ends_at, location, source) VALUES (?, ?, ?, ?, ?)",
            ("Test Event", "2023-01-01 10:00:00", "2023-01-01 11:00:00", "Test Location", "local"),
        )
        db.commit()

        # Retrieve the event
        result = db.execute("SELECT * FROM events_local WHERE title = ?", ("Test Event",)).fetchone()
        assert result is not None
        assert result["title"] == "Test Event"
        assert result["location"] == "Test Location"
        assert result["source"] == "local"

        db.close()
