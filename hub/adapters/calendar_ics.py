import logging
from datetime import datetime, timezone
from typing import List

import icalendar

from hub.cache import get_cache, set_cache
from hub.models import CalendarEvent
from hub.utils.http import RateLimitError, rate_limited_get

logger = logging.getLogger(__name__)


def _normalize(dt: datetime) -> datetime:
    """Ensure datetimes are timezone-aware (defaulting to UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch_ics_events(ics_url: str, range_start: datetime, range_end: datetime) -> List[CalendarEvent]:
    """
    Fetch and parse events from an ICS URL within the specified date range.

    Args:
        ics_url: URL to the ICS calendar
        range_start: Start of the date range
        range_end: End of the date range

    Returns:
        List of CalendarEvent objects
    """
    range_start = _normalize(range_start)
    range_end = _normalize(range_end)

    # Create cache key based on URL and date range
    cache_key = f"calendar:ics:{ics_url}:{range_start.strftime('%Y-%m-%d')}:{range_end.strftime('%Y-%m-%d')}"

    # Try to get from cache first
    cached_data = get_cache(cache_key)
    if cached_data:
        return _cached_events_from_data(cached_data)

    try:
        response = rate_limited_get(ics_url, timeout=10, service_name="calendar_ics")
        response.raise_for_status()

        # Parse the ICS data
        calendar = icalendar.Calendar.from_ical(response.text)

        events = []
        for component in calendar.walk():
            if component.name == "VEVENT":
                start = component.get("dtstart").dt
                end = component.get("dtend").dt if component.get("dtend") else start
                is_all_day = not isinstance(start, datetime)
                title = str(component.get("summary", ""))
                location = str(component.get("location", "")) if component.get("location") else None
                description = str(component.get("description", "")) if component.get("description") else None

                # Ensure start and end are datetime objects, not dates
                if not isinstance(start, datetime):
                    # If it's a date, convert to datetime at midnight
                    start = datetime.combine(start, datetime.min.time())
                if not isinstance(end, datetime):
                    # If it's a date, convert to datetime at midnight
                    end = datetime.combine(end, datetime.min.time())

                start = _normalize(start)
                end = _normalize(end)

                # Extract owner (organizer)
                organizer = component.get("organizer")
                owner = None
                if organizer:
                    if hasattr(organizer, "params"):
                        owner = organizer.params.get("CN")
                    if not owner:
                        owner = str(organizer).replace("mailto:", "").strip()

                guests = []
                attendees = component.get("attendee")
                if attendees:
                    if not isinstance(attendees, list):
                        attendees = [attendees]
                    for attendee in attendees:
                        guest = None
                        if hasattr(attendee, "params"):
                            guest = attendee.params.get("CN")
                        if not guest:
                            guest = str(attendee).replace("mailto:", "").strip()
                        if guest:
                            guests.append(guest)

                # Only include events within our range
                if range_start <= start <= range_end:
                    event = CalendarEvent(
                        title=title,
                        starts_at=start,
                        ends_at=end,
                        location=location,
                        source="ics",
                        description=description,
                        guests=guests,
                        all_day=is_all_day,
                        owner=owner,
                    )
                    events.append(event)

        # Convert events to serializable format for caching
        serializable_events = []
        for event in events:
            serializable_events.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "starts_at": event.starts_at.isoformat() if event.starts_at else None,
                    "ends_at": event.ends_at.isoformat() if event.ends_at else None,
                    "location": event.location,
                    "source": event.source,
                    "description": event.description,
                    "guests": event.guests,
                    "all_day": event.all_day,
                    "owner": event.owner,
                }
            )

        # Cache the result for 15 minutes
        set_cache(cache_key, serializable_events, ttl_seconds=900)

        return events
    except RateLimitError:
        logger.warning("ICS calendar request rate limited for %s", ics_url)
        return _cached_events_from_data(cached_data) if cached_data else []
    except Exception:
        logger.exception("Failed to fetch ICS calendar from %s", ics_url)
        return _cached_events_from_data(cached_data) if cached_data else []


def _cached_events_from_data(cached_data: List[dict]) -> List[CalendarEvent]:
    """Convert cached event payloads into CalendarEvent objects."""
    events = []
    for event_data in cached_data:
        starts_at = datetime.fromisoformat(event_data["starts_at"]) if event_data.get("starts_at") else None
        ends_at = datetime.fromisoformat(event_data["ends_at"]) if event_data.get("ends_at") else None
        if starts_at:
            starts_at = _normalize(starts_at)
        if ends_at:
            ends_at = _normalize(ends_at)
        event = CalendarEvent(
            id=event_data.get("id"),
            title=event_data.get("title", ""),
            starts_at=starts_at,
            ends_at=ends_at,
            location=event_data.get("location"),
            source=event_data.get("source", "ics"),
            description=event_data.get("description"),
            guests=event_data.get("guests"),
            all_day=bool(event_data.get("all_day")),
            owner=event_data.get("owner"),
        )
        events.append(event)
    return events
