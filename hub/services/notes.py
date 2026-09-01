from datetime import datetime, timezone
from typing import List, Optional, Union

from hub.db import get_db


def _coerce_datetime(value: Optional[Union[str, datetime]]) -> datetime:
    """Normalize database datetime values to timezone-aware UTC."""
    if value is None:
        return datetime.now(timezone.utc)

    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
    else:
        dt = value

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class Note:
    def __init__(
        self, id: Optional[int], text: str, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None
    ) -> None:
        self.id = id
        self.text = text
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "created_at": self.created_at.isoformat().replace("+00:00", "") if self.created_at else None,
            "updated_at": self.updated_at.isoformat().replace("+00:00", "") if self.updated_at else None,
        }


def list_notes() -> List[Note]:
    """Get all notes from the database."""
    db = get_db()

    query = """
        SELECT id, text, created_at, updated_at
        FROM notes
        ORDER BY created_at DESC
    """

    rows = db.execute(query).fetchall()

    notes = []
    for row in rows:
        created_at = _coerce_datetime(row["created_at"])
        updated_at = _coerce_datetime(row["updated_at"])
        note = Note(
            id=row["id"],
            text=row["text"],
            created_at=created_at,
            updated_at=updated_at,
        )
        notes.append(note)

    return notes


def create_note(text: str) -> Note:
    """Create a new note in the database."""
    db = get_db()

    query = """
        INSERT INTO notes (text)
        VALUES (?)
    """

    result = db.execute(query, (text,))
    db.commit()

    # Get the created note
    note = get_note(result.lastrowid)
    return note


def get_note(note_id: int) -> Note:
    """Get a specific note by ID."""
    db = get_db()

    query = """
        SELECT id, text, created_at, updated_at
        FROM notes
        WHERE id = ?
    """

    row = db.execute(query, (note_id,)).fetchone()

    if not row:
        return None

    created_at = _coerce_datetime(row["created_at"])
    updated_at = _coerce_datetime(row["updated_at"])

    note = Note(id=row["id"], text=row["text"], created_at=created_at, updated_at=updated_at)

    return note


def update_note(note_id: int, text: str) -> Note:
    """Update an existing note."""
    db = get_db()

    query = """
        UPDATE notes
        SET text = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """

    db.execute(query, (text, note_id))
    db.commit()

    return get_note(note_id)


def delete_note(note_id: int) -> bool:
    """Delete a note by ID."""
    db = get_db()

    query = """
        DELETE FROM notes
        WHERE id = ?
    """

    result = db.execute(query, (note_id,))
    db.commit()

    return result.rowcount > 0


def count_notes() -> int:
    """Count the total number of notes."""
    db = get_db()
    query = "SELECT COUNT(*) FROM notes"
    result = db.execute(query).fetchone()
    return result[0] if result else 0
