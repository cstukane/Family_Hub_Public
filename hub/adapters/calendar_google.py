"""Google Calendar adapter with OAuth and write support."""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Local imports intentionally after stdlib/third-party for clarity.
from hub.cache import get_cache, set_cache
from hub.models import CalendarEvent

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

logger = logging.getLogger(__name__)


def _normalize(dt: datetime) -> datetime:
    """Ensure datetimes are timezone-aware (default to UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _resolve_credentials_file(config: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Determine the path to a Google OAuth credentials file.

    Tries, in order:
        1. Explicit path supplied in config under 'credentials_file'
        2. An instance-scoped credentials.json (instance/credentials.json)
        3. A project-root credentials.json
    """
    candidate_paths: List[str] = []
    if config:
        credentials_file = config.get("credentials_file")
        if credentials_file:
            candidate_paths.append(credentials_file)

    # Default fallbacks
    candidate_paths.extend([os.path.join("instance", "credentials.json"), "credentials.json"])

    for candidate in candidate_paths:
        if not candidate:
            continue

        expanded = os.path.expanduser(candidate)
        resolved = os.path.abspath(expanded)
        if os.path.exists(resolved):
            return resolved

    return None


def get_google_calendar_credentials(config: Dict[str, Any]) -> Optional[Credentials]:
    """
    Get Google Calendar credentials using OAuth flow.

    Args:
        config: Google calendar configuration containing client_id, client_secret, and calendar_ids
    Returns:
        Google credentials object or None if authentication fails
    """
    if not config:
        return None

    creds = None

    # Token file stores the user's access and refresh tokens
    token_path = os.path.join("instance", "token.json")

    # Load existing token if available
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If there are no (valid) credentials available, let the user log in or refresh.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
            except RefreshError:
                # If refresh fails, remove the token file and start fresh
                os.remove(token_path)
                creds = None
        if not creds or not creds.valid:
            flow = None

            # Prefer an explicit credentials JSON (standard Google OAuth client secret)
            credentials_path = _resolve_credentials_file(config)
            if credentials_path:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                except FileNotFoundError:
                    # Should not happen because _resolve_credentials_file verifies existence, but guard anyway
                    flow = None
            # Fallback to legacy inline client config
            if not flow and config and config.get("client_id") and config.get("client_secret"):
                client_config = {
                    "web": {
                        "client_id": config["client_id"],
                        "client_secret": config["client_secret"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",  # nosec B105
                        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

            if not flow:
                return None

            creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(token_path, "w") as token:
                token.write(creds.to_json())

    return creds


def fetch_google_events(config: Dict[str, Any], range_start: datetime, range_end: datetime) -> List[CalendarEvent]:
    """
    Fetch and parse events from Google Calendar within the specified date range.

    Args:
        config: Google calendar configuration containing client_id, client_secret, and calendar_ids
        range_start: Start of the date range
        range_end: End of the date range
    Returns:
        List of CalendarEvent objects
    """
    range_start = _normalize(range_start)
    range_end = _normalize(range_end)

    # Create cache key based on calendar IDs and date range
    calendar_ids = config.get("calendar_ids", ["primary"])
    cache_key = (
        f"calendar:google:{':'.join(calendar_ids)}:{range_start.strftime('%Y-%m-%d')}:{range_end.strftime('%Y-%m-%d')}"
    )

    # Try to get from cache first
    cached_data = get_cache(cache_key)
    if cached_data:
        # Convert cached data back to CalendarEvent objects
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
                source=event_data.get("source", "google"),
                description=event_data.get("description"),
                guests=event_data.get("guests"),
                all_day=bool(event_data.get("all_day")),
                calendar_id=event_data.get("calendar_id"),
                owner=event_data.get("owner"),
            )
            events.append(event)
        return events

    credentials = get_google_calendar_credentials(config)
    if not credentials:
        return []

    try:
        # Build the Google Calendar service
        service = build("calendar", "v3", credentials=credentials)

        # Call the Calendar API for each calendar ID
        events = []
        for calendar_id in calendar_ids:
            # Format the time range for Google Calendar API (normalize to UTC Zulu format)
            start_time = range_start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            end_time = range_end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

            # Retrieve events from the calendar
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id, timeMin=start_time, timeMax=end_time, singleEvents=True, orderBy="startTime"
                )
                .execute()
            )

            items = events_result.get("items", [])

            for item in items:
                start_is_date = bool(item.get("start", {}).get("date"))
                end_is_date = bool(item.get("end", {}).get("date"))
                start = item["start"].get("dateTime", item["start"].get("date"))
                end = item["end"].get("dateTime", item["end"].get("date"))

                # Convert string dates to datetime objects
                starts_at = datetime.fromisoformat(start.replace("Z", "+00:00")) if start else None
                ends_at = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else None
                if starts_at:
                    starts_at = _normalize(starts_at)
                if ends_at:
                    ends_at = _normalize(ends_at)

                title = item.get("summary", "")
                location = item.get("location", None)
                description = item.get("description")
                guests = [attendee.get("email") for attendee in item.get("attendees", []) if attendee.get("email")]

                # Extract owner (creator or organizer)
                creator = item.get("creator", {})
                organizer = item.get("organizer", {})
                owner = (
                    creator.get("displayName")
                    or creator.get("email")
                    or organizer.get("displayName")
                    or organizer.get("email")
                )

                event = CalendarEvent(
                    title=title,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    location=location,
                    source="google",
                    description=description,
                    guests=guests,
                    all_day=start_is_date and end_is_date,
                    calendar_id=calendar_id,
                    owner=owner,
                )
                event.id = item.get("id")
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
                    "calendar_id": event.calendar_id,
                    "owner": event.owner,
                }
            )

        # Cache the result for 5 minutes
        set_cache(cache_key, serializable_events, ttl_seconds=300)

        return events
    except HttpError as error:
        logger.warning("Google Calendar API error while fetching events: %s", error)
        # Try to return cached data if available, even if expired
        cached_data = get_cache(cache_key)
        if cached_data:
            # Convert cached data back to CalendarEvent objects
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
                    source=event_data.get("source", "google"),
                    description=event_data.get("description"),
                    guests=event_data.get("guests"),
                    all_day=bool(event_data.get("all_day")),
                    calendar_id=event_data.get("calendar_id"),
                    owner=event_data.get("owner"),
                )
                events.append(event)
            return events
        return []
    except Exception:
        logger.exception("Unexpected error while fetching Google Calendar events")
        return []


GOOGLE_EVENT_COLOR_MAP = {
    "blue": "9",
    "green": "10",
    "red": "11",
    "yellow": "5",
    "purple": "3",
    "orange": "6",
}


def add_google_event(
    config: Dict[str, Any],
    title: str,
    starts_at: datetime,
    ends_at: datetime,
    location: Optional[str] = None,
    description: Optional[str] = None,
    all_day: bool = False,
    calendar_id: Optional[str] = None,
    guests: Optional[List[str]] = None,
    reminders: Optional[List[Union[str, int]]] = None,
    visibility: Optional[str] = None,
    color: Optional[str] = None,
    recurrence: Optional[List[str]] = None,
) -> Optional[CalendarEvent]:
    """
    Add a new event to Google Calendar.

    Args:
        config: Google calendar configuration containing client_id, client_secret, and calendar_ids
        title: Event title
        starts_at: Start time of the event
        ends_at: End time of the event
        location: Optional location of the event
    Returns:
        The created CalendarEvent object or None if failed
    """
    credentials = get_google_calendar_credentials(config)
    if not credentials:
        return None

    try:
        # Build the Google Calendar service
        service = build("calendar", "v3", credentials=credentials)

        # Get the primary calendar or first calendar ID
        target_calendar_id = calendar_id
        if not target_calendar_id:
            target_calendar_id = config.get("calendar_ids", ["primary"])[0]

        # Prepare event data
        event_data: Dict[str, Any] = {"summary": title}
        if location:
            event_data["location"] = location
        if description:
            event_data["description"] = description

        local_timezone = datetime.now().astimezone().tzinfo
        start_dt = starts_at if starts_at.tzinfo else starts_at.replace(tzinfo=local_timezone)
        end_dt = ends_at if ends_at.tzinfo else ends_at.replace(tzinfo=local_timezone)

        if all_day:
            # Google treats all-day events as date-only with exclusive end date
            start_date = start_dt.date()
            end_date = end_dt.date() + timedelta(days=1)
            event_data["start"] = {"date": start_date.isoformat()}
            event_data["end"] = {"date": end_date.isoformat()}
        else:
            event_data["start"] = {"dateTime": start_dt.isoformat()}
            event_data["end"] = {"dateTime": end_dt.isoformat()}

        if guests:
            attendees = [{"email": email} for email in guests if email]
            if attendees:
                event_data["attendees"] = attendees

        if reminders:
            overrides = []
            for reminder in reminders:
                if isinstance(reminder, str) and reminder.lower() in {"none", "default"}:
                    overrides = []
                    break
                try:
                    minutes = int(reminder)
                    overrides.append({"method": "popup", "minutes": minutes})
                except (TypeError, ValueError):
                    continue
            if overrides:
                event_data["reminders"] = {"useDefault": False, "overrides": overrides}
            else:
                event_data["reminders"] = {"useDefault": True}

        if visibility and visibility.lower() != "default":
            event_data["visibility"] = visibility.lower()

        if color:
            color_id = GOOGLE_EVENT_COLOR_MAP.get(color.lower())
            if color_id:
                event_data["colorId"] = color_id

        if recurrence:
            event_data["recurrence"] = recurrence

        # Create the event
        event = service.events().insert(calendarId=target_calendar_id, body=event_data).execute()

        # Convert the response to a CalendarEvent object
        created_event = CalendarEvent(
            title=event.get("summary", ""),
            starts_at=start_dt,
            ends_at=end_dt,
            location=event.get("location"),
            source="google",
            description=event.get("description"),
            all_day=all_day,
            visibility=event.get("visibility"),
            color=color,
            calendar_id=target_calendar_id,
            guests=[attendee.get("email") for attendee in event.get("attendees", []) if attendee.get("email")],
            reminders=reminders,
        )
        created_event.id = event.get("id")

        return created_event
    except HttpError as error:
        logger.warning("Google Calendar API error while adding event: %s", error)
        return None
    except Exception:
        logger.exception("Unexpected error while adding Google Calendar event")
        return None


def delete_google_event(config: Dict[str, Any], event_id: str, calendar_id: Optional[str] = None) -> bool:
    """
    Delete an event from Google Calendar.

    Args:
        config: Google calendar configuration containing client_id, client_secret, and calendar_ids
        event_id: ID of the event to delete
    Returns:
        True if successful, False otherwise
    """
    credentials = get_google_calendar_credentials(config)
    if not credentials:
        return False

    try:
        # Build the Google Calendar service
        service = build("calendar", "v3", credentials=credentials)

        # Get the primary calendar or first calendar ID
        if isinstance(config, dict):
            calendar_ids = config.get("calendar_ids") or []
        else:
            calendar_ids = getattr(config, "calendar_ids", None) or []
        target_calendar_id = calendar_id or (calendar_ids[0] if calendar_ids else "primary")

        # Delete the event
        service.events().delete(calendarId=target_calendar_id, eventId=event_id).execute()

        return True
    except HttpError as error:
        logger.warning("Google Calendar API error while deleting event: %s", error)
        return False
    except Exception:
        logger.exception("Unexpected error while deleting Google Calendar event")
        return False


def get_calendar_status(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get the status of the Google Calendar integration.

    Args:
        config: Google calendar configuration
    Returns:
        Dictionary with status information
    """
    credentials = get_google_calendar_credentials(config)

    if not credentials:
        return {"status": "Google Calendar not authenticated", "source": "Google", "connected": False}

    return {
        "status": "Google Calendar authenticated and connected",
        "source": "Google",
        "connected": True,
        "calendar_ids": config.get("calendar_ids", ["primary"]),
    }
