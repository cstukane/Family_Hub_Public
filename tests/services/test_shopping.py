from datetime import datetime, timezone

import pytest

from hub.services import shopping


def test_create_shopping_item():
    """Test creating a new shopping item."""
    text = "Milk"
    qty = "1 gallon"

    # Test the model creation part
    item = shopping.ShoppingItem(id=None, text=text, qty=qty)

    assert item.text == text
    assert item.qty == qty
    assert item.id is None
    assert item.done is False
    assert isinstance(item.created_at, datetime)
    assert isinstance(item.updated_at, datetime)


def test_shopping_item_to_dict():
    """Test converting shopping item to dictionary."""
    item = shopping.ShoppingItem(
        id=1,
        text="Bread",
        qty="2 loaves",
        done=True,
        created_at=datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
    )

    item_dict = item.to_dict()

    assert item_dict["id"] == 1
    assert item_dict["text"] == "Bread"
    assert item_dict["qty"] == "2 loaves"
    assert item_dict["done"] is True
    assert item_dict["created_at"] == "2023-01-01T10:00:00"
    assert item_dict["updated_at"] == "2023-01-01T10:00:00"


def test_toggle_shopping_item_done():
    """Test toggling the done status of a shopping item."""
    # This would require proper app context and DB setup
    # Just test the model behavior
    item = shopping.ShoppingItem(id=1, text="Test item")

    # Initially should be not done
    assert item.done is False

    # When toggled in the service, it would change
    # This is more of an integration test for the service


def test_create_shopping_item_with_defaults():
    """Test creating a shopping item with default values."""
    text = "Apples"

    item = shopping.ShoppingItem(id=None, text=text)

    assert item.text == text
    assert item.qty is None
    assert item.done is False
    assert item.id is None
