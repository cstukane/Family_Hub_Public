"""Service for managing chores and chore assignments"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from hub.db import get_db


def _parse_datetime(dt_value):
    """Parse datetime value from database, handling both string and datetime objects."""
    if dt_value is None:
        return None

    if isinstance(dt_value, datetime):
        return dt_value

    if isinstance(dt_value, str):
        try:
            return datetime.fromisoformat(dt_value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    return None


class Chore:
    """Represents a chore with all its properties."""

    def __init__(
        self,
        id=None,
        title="",
        assignee="",
        due_date=None,
        completed=False,
        recurring_schedule=None,
        priority="normal",
        description="",
        created_at=None,
        updated_at=None,
        completed_at=None,
        family_member="",
    ):
        self.id = id
        self.title = title
        self.assignee = assignee or family_member  # Backward compatibility
        self.due_date = _parse_datetime(due_date) if due_date else None
        self.completed = completed
        self.recurring_schedule = recurring_schedule
        self.priority = priority
        self.description = description
        self.created_at = _parse_datetime(created_at) if created_at else datetime.now()
        self.updated_at = _parse_datetime(updated_at) if updated_at else datetime.now()
        self.completed_at = _parse_datetime(completed_at) if completed_at else None

    def to_dict(self):
        """Convert chore to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "assignee": self.assignee,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed": self.completed,
            "recurring_schedule": self.recurring_schedule,
            "priority": self.priority,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def __repr__(self):
        return f"<Chore(id={self.id}, title='{self.title}', assignee='{self.assignee}')>"


class ChoreService:
    """Service class for managing chores."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_chore(
        self,
        title: str,
        assignee: str,
        due_date: Optional[datetime] = None,
        recurring_schedule: Optional[str] = None,
        priority: str = "normal",
        description: str = "",
        family_member: Optional[str] = None,
    ) -> Optional[Chore]:
        """Create a new chore."""
        try:
            db = get_db()

            assignee = assignee or family_member  # Backward compatibility

            query = """
                INSERT INTO chores (title, assignee, due_date, completed, recurring_schedule, priority, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            result = db.execute(
                query,
                (
                    title,
                    assignee,
                    due_date.isoformat() if due_date else None,
                    0,
                    recurring_schedule,
                    priority,
                    description,
                ),
            )
            db.commit()

            # Return the created chore
            return self.get_chore(result.lastrowid)
        except Exception as e:
            self.logger.error(f"Error creating chore: {e}")
            return None

    def get_chore(self, chore_id: int) -> Optional[Chore]:
        """Get a specific chore by ID."""
        try:
            db = get_db()

            query = """
                SELECT id, title, assignee, due_date, completed, recurring_schedule, priority, description,
                       created_at, updated_at, completed_at
                FROM chores
                WHERE id = ?
            """

            row = db.execute(query, (chore_id,)).fetchone()
            if not row:
                return None

            return Chore(
                id=row["id"],
                title=row["title"],
                assignee=row["assignee"],
                due_date=row["due_date"],
                completed=bool(row["completed"]),
                recurring_schedule=row["recurring_schedule"],
                priority=row["priority"],
                description=row["description"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                completed_at=row["completed_at"],
            )
        except Exception as e:
            self.logger.error(f"Error fetching chore {chore_id}: {e}")
            return None

    def get_chores(self, assignee: Optional[str] = None, completed: Optional[bool] = None) -> List[Chore]:
        """Get all chores with optional filtering."""
        try:
            db = get_db()

            query = """
                SELECT id, title, assignee, due_date, completed, recurring_schedule, priority, description,
                       created_at, updated_at, completed_at
                FROM chores
                WHERE 1=1
            """
            params = []

            if assignee is not None:
                query += " AND assignee = ?"
                params.append(assignee)

            if completed is not None:
                query += " AND completed = ?"
                params.append(int(completed))

            query += " ORDER BY CASE priority "
            query += "WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'normal' THEN 3 WHEN 'low' THEN 4 ELSE 5 END, "
            query += "due_date ASC"

            rows = db.execute(query, params).fetchall()

            chores = []
            for row in rows:
                chore = Chore(
                    id=row["id"],
                    title=row["title"],
                    assignee=row["assignee"],
                    due_date=row["due_date"],
                    completed=bool(row["completed"]),
                    recurring_schedule=row["recurring_schedule"],
                    priority=row["priority"],
                    description=row["description"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    completed_at=row["completed_at"],
                )
                chores.append(chore)

            return chores
        except Exception as e:
            self.logger.error(f"Error fetching chores: {e}")
            return []

    def update_chore(
        self,
        chore_id: int,
        title: Optional[str] = None,
        assignee: Optional[str] = None,
        due_date: Optional[datetime] = None,
        completed: Optional[bool] = None,
        recurring_schedule: Optional[str] = None,
        priority: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Chore]:
        """Update an existing chore."""
        try:
            db = get_db()

            # First get the current chore to check if it exists
            current_chore = self.get_chore(chore_id)
            if not current_chore:
                return None

            # Prepare update query and parameters
            update_fields = []
            params = []

            if title is not None:
                update_fields.append("title = ?")
                params.append(title)

            if assignee is not None:
                update_fields.append("assignee = ?")
                params.append(assignee)

            if due_date is not None:
                update_fields.append("due_date = ?")
                params.append(due_date.isoformat() if due_date else None)

            if completed is not None:
                update_fields.append("completed = ?")
                params.append(int(completed))
                # Update completed_at if being marked as completed
                if completed and not current_chore.completed:
                    update_fields.append("completed_at = ?")
                    params.append(datetime.now().isoformat())
                # Clear completed_at if being marked as incomplete
                elif not completed and current_chore.completed:
                    update_fields.append("completed_at = NULL")

            if recurring_schedule is not None:
                update_fields.append("recurring_schedule = ?")
                params.append(recurring_schedule)

            if priority is not None:
                update_fields.append("priority = ?")
                params.append(priority)

            if description is not None:
                update_fields.append("description = ?")
                params.append(description)

            # Always update the updated_at timestamp
            update_fields.append("updated_at = ?")
            params.append(datetime.now().isoformat())

            if not update_fields:
                return current_chore  # No changes to make

            query = f"UPDATE chores SET {', '.join(update_fields)} WHERE id = ?"  # nosec B608
            params.append(chore_id)

            db.execute(query, params)
            db.commit()

            # Return the updated chore
            return self.get_chore(chore_id)
        except Exception as e:
            self.logger.error(f"Error updating chore {chore_id}: {e}")
            return None

    def delete_chore(self, chore_id: int) -> bool:
        """Delete a chore by ID."""
        try:
            db = get_db()

            query = "DELETE FROM chores WHERE id = ?"
            result = db.execute(query, (chore_id,))
            db.commit()

            return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting chore {chore_id}: {e}")
            return False

    def complete_chore(self, chore_id: int) -> Optional[Chore]:
        """Mark a chore as completed."""
        return self.update_chore(chore_id, completed=True)

    def uncomplete_chore(self, chore_id: int) -> Optional[Chore]:
        """Mark a chore as incomplete."""
        return self.update_chore(chore_id, completed=False)

    def get_chores_due_soon(self, days: int = 7) -> List[Chore]:
        """Get chores that are due within the specified number of days."""
        try:
            db = get_db()

            now = datetime.now()
            future_date = now + timedelta(days=days)

            query = """
                SELECT id, title, assignee, due_date, completed, recurring_schedule, priority, description,
                       created_at, updated_at, completed_at
                FROM chores
                WHERE completed = 0
                AND due_date IS NOT NULL
                AND due_date BETWEEN ? AND ?
                ORDER BY due_date ASC
            """

            rows = db.execute(query, (now.isoformat(), future_date.isoformat())).fetchall()

            chores = []
            for row in rows:
                chore = Chore(
                    id=row["id"],
                    title=row["title"],
                    assignee=row["assignee"],
                    due_date=row["due_date"],
                    completed=bool(row["completed"]),
                    recurring_schedule=row["recurring_schedule"],
                    priority=row["priority"],
                    description=row["description"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    completed_at=row["completed_at"],
                )
                chores.append(chore)

            return chores
        except Exception as e:
            self.logger.error(f"Error fetching chores due soon: {e}")
            return []

    def get_overdue_chores(self) -> List[Chore]:
        """Get chores that are past their due date."""
        try:
            db = get_db()

            now = datetime.now()

            query = """
                SELECT id, title, assignee, due_date, completed, recurring_schedule, priority, description,
                       created_at, updated_at, completed_at
                FROM chores
                WHERE completed = 0
                AND due_date IS NOT NULL
                AND due_date < ?
                ORDER BY due_date ASC
            """

            rows = db.execute(query, (now.isoformat(),)).fetchall()

            chores = []
            for row in rows:
                chore = Chore(
                    id=row["id"],
                    title=row["title"],
                    assignee=row["assignee"],
                    due_date=row["due_date"],
                    completed=bool(row["completed"]),
                    recurring_schedule=row["recurring_schedule"],
                    priority=row["priority"],
                    description=row["description"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    completed_at=row["completed_at"],
                )
                chores.append(chore)

            return chores
        except Exception as e:
            self.logger.error(f"Error fetching overdue chores: {e}")
            return []

    def create_recurring_chore_instance(self, original_chore_id: int) -> Optional[Chore]:
        """Create a new instance of a recurring chore based on the original."""
        try:
            original_chore = self.get_chore(original_chore_id)
            if not original_chore or not original_chore.recurring_schedule:
                return None

            # Calculate the next occurrence based on the recurring schedule
            next_due_date = self._calculate_next_occurrence(original_chore)
            if not next_due_date:
                return None

            # Create a new chore instance with the same properties but updated due date
            new_chore = self.create_chore(
                title=original_chore.title,
                assignee=original_chore.assignee,
                due_date=next_due_date,
                recurring_schedule=original_chore.recurring_schedule,
                priority=original_chore.priority,
                description=original_chore.description,
            )

            return new_chore
        except Exception as e:
            self.logger.error(f"Error creating recurring chore instance: {e}")
            return None

    def _calculate_next_occurrence(self, chore: Chore) -> Optional[datetime]:
        """Calculate the next occurrence date for a recurring chore."""
        if not chore.due_date or not chore.recurring_schedule:
            return None

        last_due_date = chore.due_date

        if chore.recurring_schedule == "daily":
            return last_due_date + timedelta(days=1)
        elif chore.recurring_schedule == "weekly":
            return last_due_date + timedelta(weeks=1)
        elif chore.recurring_schedule == "monthly":
            # Add approximately one month (30 days)
            return last_due_date + timedelta(days=30)
        elif chore.recurring_schedule == "yearly":
            return last_due_date + timedelta(days=365)
        elif chore.recurring_schedule.startswith("every_") and chore.recurring_schedule.endswith("_days"):
            # Parse format like "every_3_days", "every_10_days"
            try:
                days = int(chore.recurring_schedule.split("_")[1])
                return last_due_date + timedelta(days=days)
            except (ValueError, IndexError):
                return None
        else:
            # Unknown recurring pattern
            return None


# Global instance of the chore service
chore_service = ChoreService()
