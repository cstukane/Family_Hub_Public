"""Tests for the cooking service."""

import os
import tempfile
from unittest.mock import patch

import pytest

from app import create_app
from hub.services.cooking import (
    add_ingredients_to_shopping_list,
    create_recipe,
    get_all_recipes,
    get_recipe,
    toggle_ingredient_check,
)


class TestCookingService:
    """Test cases for the cooking service with Flask app context."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a temporary database file for testing
        self.db_fd, self.db_path = tempfile.mkstemp()
        os.close(self.db_fd)
        self.db_fd = None

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["DATABASE"] = self.db_path

        # Mock the scheduler and timer monitor to prevent them from starting during tests
        with (
            patch("hub.scheduler.create_scheduler"),
            patch("hub.sockets.start_timer_monitor"),
            patch("flask_socketio.SocketIO"),
        ):
            with self.app.app_context():
                from hub.db import init_db

                init_db()

    def teardown_method(self):
        """Tear down test fixtures after each test method."""
        os.unlink(self.db_path)

    def test_create_recipe(self):
        """Test creating a recipe."""
        with self.app.app_context():
            title = "Test Recipe"
            ingredients = ["ingredient1", "ingredient2"]
            steps = ["step1", "step2"]
            prep_time = 10
            cook_time = 20

            recipe = create_recipe(title, ingredients, steps, prep_time, cook_time)

            assert recipe is not None
            assert recipe.title == title
            assert recipe.ingredients == ingredients
            assert recipe.steps == steps
            assert recipe.prep_time == prep_time
            assert recipe.cook_time == cook_time

    def test_get_recipe(self):
        """Test retrieving a recipe."""
        with self.app.app_context():
            title = "Test Recipe"
            ingredients = ["ingredient1", "ingredient2"]
            steps = ["step1", "step2"]

            # Create a recipe first
            created_recipe = create_recipe(title, ingredients, steps)
            assert created_recipe is not None

            # Retrieve the recipe by ID
            retrieved_recipe = get_recipe(created_recipe.id)

            assert retrieved_recipe is not None
            assert retrieved_recipe.id == created_recipe.id
            assert retrieved_recipe.title == created_recipe.title
            assert retrieved_recipe.ingredients == created_recipe.ingredients
            assert retrieved_recipe.steps == created_recipe.steps

    def test_get_all_recipes(self):
        """Test retrieving all recipes."""
        with self.app.app_context():
            # Clear any existing recipes by creating a known recipe
            title = "All Recipes Test"
            ingredients = ["test_ingredient"]
            steps = ["test_step"]

            created_recipe = create_recipe(title, ingredients, steps)
            assert created_recipe is not None

            # Get all recipes
            all_recipes = get_all_recipes()

            # Check if our recipe is in the list
            found_recipe = next((r for r in all_recipes if r.id == created_recipe.id), None)
            assert found_recipe is not None
            assert found_recipe.title == title

    def test_add_ingredients_to_shopping_list(self):
        """Test adding recipe ingredients to shopping list."""
        with self.app.app_context():
            # First, create a recipe with some ingredients
            title = "Shopping Test Recipe"
            ingredients = ["flour", "sugar", "eggs"]
            steps = ["mix", "bake"]

            recipe = create_recipe(title, ingredients, steps)
            assert recipe is not None
            assert len(recipe.ingredients) == 3

            # Add ingredients to shopping list
            added_count = add_ingredients_to_shopping_list(recipe.id)

            # Verify the count matches the number of ingredients
            assert added_count == len(recipe.ingredients)

    def test_toggle_ingredient_check(self):
        """Test toggling an ingredient check status."""
        with self.app.app_context():
            # Create a recipe
            title = "Toggle Test Recipe"
            ingredients = ["ingredient1", "ingredient2"]
            steps = ["step1"]

            recipe = create_recipe(title, ingredients, steps)
            assert recipe is not None

            # Try to toggle the first ingredient (index 0)
            result = toggle_ingredient_check(recipe.id, 0)
            assert result is True

            # Try to toggle with invalid index
            result = toggle_ingredient_check(recipe.id, 99)  # Invalid index
            assert result is False


if __name__ == "__main__":
    pytest.main()
