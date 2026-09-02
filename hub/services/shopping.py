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


class ShoppingItem:
    def __init__(
        self,
        id: Optional[int],
        text: str,
        done: bool = False,
        qty: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.text = text
        self.done = done
        self.qty = qty
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "done": self.done,
            "qty": self.qty,
            "created_at": self.created_at.isoformat().replace("+00:00", "") if self.created_at else None,
            "updated_at": self.updated_at.isoformat().replace("+00:00", "") if self.updated_at else None,
        }


def list_shopping_items() -> List[ShoppingItem]:
    """Get all shopping items from the database."""
    db = get_db()

    query = """
        SELECT id, text, done, qty, created_at, updated_at
        FROM shopping_items
        ORDER BY created_at DESC
    """

    rows = db.execute(query).fetchall()

    items = []
    for row in rows:
        created_at = _coerce_datetime(row["created_at"])
        updated_at = _coerce_datetime(row["updated_at"])
        item = ShoppingItem(
            id=row["id"],
            text=row["text"],
            done=bool(row["done"]),
            qty=row["qty"],
            created_at=created_at,
            updated_at=updated_at,
        )
        items.append(item)

    return items


def create_shopping_item(text: str, qty: Optional[str] = None) -> ShoppingItem:
    """Create a new shopping item in the database."""
    db = get_db()

    query = """
        INSERT INTO shopping_items (text, qty)
        VALUES (?, ?)
    """

    result = db.execute(query, (text, qty))
    db.commit()

    # Get the created item
    item = get_shopping_item(result.lastrowid)
    return item


def get_shopping_item(item_id: int) -> ShoppingItem:
    """Get a specific shopping item by ID."""
    db = get_db()

    query = """
        SELECT id, text, done, qty, created_at, updated_at
        FROM shopping_items
        WHERE id = ?
    """

    row = db.execute(query, (item_id,)).fetchone()

    if not row:
        return None

    created_at = _coerce_datetime(row["created_at"])
    updated_at = _coerce_datetime(row["updated_at"])

    item = ShoppingItem(
        id=row["id"],
        text=row["text"],
        done=bool(row["done"]),
        qty=row["qty"],
        created_at=created_at,
        updated_at=updated_at,
    )

    return item


def update_shopping_item(
    item_id: int, text: Optional[str] = None, done: Optional[bool] = None, qty: Optional[str] = None
) -> ShoppingItem:
    """Update an existing shopping item."""
    item = get_shopping_item(item_id)
    if not item:
        return None

    db = get_db()

    # Build the update query dynamically based on provided fields
    updates = []
    params = []

    if text is not None:
        updates.append("text = ?")
        params.append(text)

    if done is not None:
        updates.append("done = ?")
        params.append(int(done))

    if qty is not None:
        updates.append("qty = ?")
        params.append(qty)

    # Always update the timestamp
    updates.append("updated_at = CURRENT_TIMESTAMP")

    query = f"UPDATE shopping_items SET {', '.join(updates)} WHERE id = ?"  # nosec B608
    params.append(item_id)

    db.execute(query, params)
    db.commit()

    return get_shopping_item(item_id)


def delete_shopping_item(item_id: int) -> bool:
    """Delete a shopping item by ID."""
    db = get_db()

    query = """
        DELETE FROM shopping_items
        WHERE id = ?
    """

    result = db.execute(query, (item_id,))
    db.commit()

    return result.rowcount > 0


def toggle_shopping_item_done(item_id: int) -> ShoppingItem:
    """Toggle the 'done' status of a shopping item."""
    item = get_shopping_item(item_id)
    if not item:
        return None

    return update_shopping_item(item_id, done=not item.done)


def count_active_shopping_items() -> int:
    """Count the number of active (not done) shopping items."""
    db = get_db()
    query = "SELECT COUNT(*) FROM shopping_items WHERE done = 0"
    result = db.execute(query).fetchone()
    return result[0] if result else 0
