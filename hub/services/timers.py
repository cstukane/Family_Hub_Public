from datetime import datetime, timedelta, timezone
from typing import List, Optional

from hub.db import get_db
from hub.models import Timer


def _to_utc_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """Normalize database values to timezone-aware UTC datetimes."""
    if value is None:
        return None
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
    else:
        dt = value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def create_timer(label: str, seconds: int) -> Timer:
    """
    Create a new timer.

    Args:
        label: Timer label/description
        seconds: Number of seconds for the timer

    Returns:
        Created Timer object
    """
    db = get_db()

    ends_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    ends_at_str = ends_at.astimezone(timezone.utc).isoformat()

    query = """
        INSERT INTO timers (label, ends_at, active)
        VALUES (?, ?, ?)
    """
    result = db.execute(query, (label, ends_at_str, 1))
    db.commit()

    # Create and return the new timer
    timer = Timer(id=result.lastrowid, label=label, ends_at=ends_at, active=True)
    return timer


def get_timer(timer_id: int) -> Optional[Timer]:
    """
    Get a specific timer by ID.

    Args:
        timer_id: ID of the timer to retrieve

    Returns:
        Timer object or None if not found
    """
    db = get_db()

    query = """
        SELECT id, label, ends_at, active
        FROM timers
        WHERE id = ?
    """

    row = db.execute(query, (timer_id,)).fetchone()

    if not row:
        return None

    # Handle SQLite timestamp format
    ends_at_val = row["ends_at"]
    ends_at = None
    if ends_at_val:
        ends_at = _to_utc_datetime(ends_at_val)

    return Timer(id=row["id"], label=row["label"], ends_at=ends_at, active=bool(row["active"]))


def list_active_timers() -> List[Timer]:
    """
    Get all active timers.

    Returns:
        List of active Timer objects
    """
    db = get_db()

    query = """
        SELECT id, label, ends_at, active
        FROM timers
        WHERE active = 1
        ORDER BY ends_at
    """

    rows = db.execute(query).fetchall()

    timers = []
    for row in rows:
        # Handle SQLite timestamp format
        ends_at_val = row["ends_at"]
        ends_at = None
        if ends_at_val:
            ends_at = _to_utc_datetime(ends_at_val)

        timer = Timer(id=row["id"], label=row["label"], ends_at=ends_at, active=bool(row["active"]))
        timers.append(timer)

    return timers


def delete_timer(timer_id: int) -> bool:
    """
    Delete a timer.

    Args:
        timer_id: ID of the timer to delete

    Returns:
        True if successful, False otherwise
    """
    db = get_db()

    query = "DELETE FROM timers WHERE id = ?"
    result = db.execute(query, (timer_id,))
    db.commit()

    return result.rowcount > 0


def update_timer(
    timer_id: int, label: Optional[str] = None, seconds: Optional[int] = None, active: Optional[bool] = None
) -> Optional[Timer]:
    """
    Update a timer.

    Args:
        timer_id: ID of the timer to update
        label: New label (optional)
        seconds: New seconds from now (optional)
        active: New active state (optional)

    Returns:
        Updated Timer object or None if not found
    """
    # First get the existing timer
    existing_timer = get_timer(timer_id)
    if not existing_timer:
        return None

    # Prepare update values
    new_label = label if label is not None else existing_timer.label
    new_active = active if active is not None else existing_timer.active

    # Calculate new end time if seconds is provided
    if seconds is not None:
        new_ends_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    else:
        new_ends_at = existing_timer.ends_at

    db = get_db()

    query = """
        UPDATE timers
        SET label = ?, ends_at = ?, active = ?
        WHERE id = ?
    """

    new_ends_at_str = new_ends_at.astimezone(timezone.utc).isoformat() if new_ends_at else None

    result = db.execute(query, (new_label, new_ends_at_str, new_active, timer_id))
    db.commit()

    if result.rowcount > 0:
        return Timer(id=timer_id, label=new_label, ends_at=new_ends_at, active=new_active)

    return None


def check_expired_timers() -> List[Timer]:
    """
    Check and return expired timers that are still active.

    Returns:
        List of expired Timer objects
    """
    db = get_db()

    now = datetime.now(timezone.utc)

    query = """
        SELECT id, label, ends_at, active
        FROM timers
        WHERE active = 1
    """

    rows = db.execute(query).fetchall()

    expired_timers = []
    for row in rows:
        # Handle SQLite timestamp format
        ends_at_val = row["ends_at"]
        ends_at = None
        if ends_at_val:
            ends_at = _to_utc_datetime(ends_at_val)

        timer = Timer(id=row["id"], label=row["label"], ends_at=ends_at, active=bool(row["active"]))
        if timer.ends_at and timer.ends_at <= now:
            expired_timers.append(timer)

    return expired_timers


def deactivate_expired_timers() -> int:
    """
    Deactivate all expired timers.

    Returns:
        Number of timers deactivated
    """
    expired = check_expired_timers()
    if not expired:
        return 0

    db = get_db()
    ids = [timer.id for timer in expired if timer.id is not None]
    if not ids:
        return 0

    placeholders = ",".join("?" for _ in ids)
    query = f"""
        UPDATE timers
        SET active = 0
        WHERE id IN ({placeholders})
    """  # nosec B608

    result = db.execute(query, ids)
    db.commit()

    return result.rowcount


def count_active_timers() -> int:
    """Count the number of active timers."""
    db = get_db()
    query = "SELECT COUNT(*) FROM timers WHERE active = 1"
    result = db.execute(query).fetchone()
    return result[0] if result else 0
