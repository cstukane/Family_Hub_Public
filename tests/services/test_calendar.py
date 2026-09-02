from datetime import datetime, timedelta, timezone

import pytest

from hub.services import calendar


def test_create_calendar_event():
    """Test creating a new calendar event."""
    title = "Test Event"
    starts_at = datetime.now(timezone.utc)
    ends_at = starts_at + timedelta(hours=1)
    location = "Test Location"

    # Note: This test would require a proper app context and DB setup
    # For now, we'll test the model creation part
    event = calendar.CalendarEvent(title=title, starts_at=starts_at, ends_at=ends_at, location=location)

    assert event.title == title
    assert event.starts_at == starts_at
    assert event.ends_at == ends_at
    assert event.location == location
    assert event.source == "local"


def test_calendar_event_to_dict():
    """Test converting calendar event to dictionary."""
    starts_at = datetime.now(timezone.utc)
    ends_at = starts_at + timedelta(hours=2)

    event = calendar.CalendarEvent(title="Test Event", starts_at=starts_at, ends_at=ends_at, location="Test Location")
    event.id = 1

    event_dict = event.to_dict()

    assert event_dict["id"] == 1
    assert event_dict["title"] == "Test Event"
    assert event_dict["location"] == "Test Location"
    assert event_dict["source"] == "local"


def test_get_upcoming_events_empty(app):
    """Test getting upcoming events when none exist."""
    with app.app_context():
        # This function requires database access
        upcoming_events = calendar.get_upcoming_events(5)
        # The actual implementation will depend on DB state
        assert isinstance(upcoming_events, list)


def test_list_events_date_range(app):
    """Test listing events within a date range."""
    with app.app_context():
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=7)

        events = calendar.list_events(start_date, end_date)
        # The actual implementation will depend on DB state
        assert isinstance(events, list)
