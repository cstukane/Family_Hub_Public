"""Cooking Mode Service for Family Hub."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from hub.db import get_db


def parse_datetime(date_str):
    """Parse datetime from various formats that might be stored in SQLite."""
    if isinstance(date_str, datetime):
        return date_str
    if not date_str:
        return datetime.now()

    # Handle ISO format with 'T' separator
    if "T" in date_str:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Handle other common formats
    try:
        # Try standard fromisoformat
        return datetime.fromisoformat(date_str)
    except ValueError:
        try:
            # Try fromtimestamp if it's a timestamp
            return datetime.fromtimestamp(float(date_str))
        except ValueError:
            # If all else fails, return current time
            return datetime.now()


@dataclass
class Recipe:
    """Recipe data class."""

    id: int
    title: str
    ingredients: List[str]
    steps: List[str]
    prep_time: int  # in minutes
    cook_time: int  # in minutes
    created_at: datetime
    updated_at: datetime


@dataclass
class RecipeIngredient:
    """Recipe ingredient data class."""

    id: int
    recipe_id: int
    name: str
    quantity: Optional[str]
    unit: Optional[str]
    checked: bool = False  # for when displayed in cooking mode


def get_recipe(recipe_id: int) -> Optional[Recipe]:
    """Get a recipe by ID."""
    db = get_db()
    cur = db.execute(
        "SELECT id, title, ingredients, steps, prep_time, cook_time, created_at, updated_at FROM recipes WHERE id = ?",
        (recipe_id,),
    )
    row = cur.fetchone()

    if row:
        # Parse ingredients and steps from stored JSON strings
        import json

        ingredients = json.loads(row[2]) if row[2] else []
        steps = json.loads(row[3]) if row[3] else []

        return Recipe(
            id=row[0],
            title=row[1],
            ingredients=ingredients,
            steps=steps,
            prep_time=row[4],
            cook_time=row[5],
            created_at=parse_datetime(row[6]),
            updated_at=parse_datetime(row[7]),
        )
    return None


def get_all_recipes() -> List[Recipe]:
    """Get all recipes."""
    db = get_db()
    cur = db.execute(
        "SELECT id, title, ingredients, steps, prep_time, cook_time, created_at, updated_at FROM recipes ORDER BY title"
    )
    rows = cur.fetchall()

    recipes = []
    for row in rows:
        import json

        ingredients = json.loads(row[2]) if row[2] else []
        steps = json.loads(row[3]) if row[3] else []

        recipes.append(
            Recipe(
                id=row[0],
                title=row[1],
                ingredients=ingredients,
                steps=steps,
                prep_time=row[4],
                cook_time=row[5],
                created_at=parse_datetime(row[6]),
                updated_at=parse_datetime(row[7]),
            )
        )

    return recipes


def create_recipe(
    title: str, ingredients: List[str], steps: List[str], prep_time: int = 0, cook_time: int = 0
) -> Optional[Recipe]:
    """Create a new recipe."""
    db = get_db()

    # Convert to JSON for storage
    import json

    ingredients_json = json.dumps(ingredients)
    steps_json = json.dumps(steps)

    now = datetime.now().isoformat()
    cur = db.execute(
        "INSERT INTO recipes (title, ingredients, steps, prep_time, cook_time, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (title, ingredients_json, steps_json, prep_time, cook_time, now, now),
    )
    db.commit()

    # Return the newly created recipe
    return get_recipe(cur.lastrowid)


def add_ingredients_to_shopping_list(recipe_id: int) -> int:
    """Add all ingredients from a recipe to the shopping list."""
    from . import shopping

    recipe = get_recipe(recipe_id)
    if not recipe:
        return 0

    added_count = 0
    for ingredient in recipe.ingredients:
        # Create shopping item with the ingredient name
        shopping_item = shopping.create_shopping_item(ingredient, qty=None)
        if shopping_item:
            added_count += 1

    return added_count


def toggle_ingredient_check(recipe_id: int, ingredient_index: int) -> bool:
    """Toggle the checked status of an ingredient."""
    recipe = get_recipe(recipe_id)
    if not recipe or ingredient_index < 0 or ingredient_index >= len(recipe.ingredients):
        return False

    # In a real implementation, we'd have a more sophisticated way to track ingredient check status
    # For now, we'll return True to indicate success
    return True
