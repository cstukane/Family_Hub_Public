import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app import group_events_by_date_for_template
from hub.models import CalendarEvent
from hub.routes import api as api_routes
from hub.services.shopping import ShoppingItem

# HTTP Status Codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400


def test_get_notes_partial(client):
    """Test getting the notes partial."""
    response = client.get("/partials/notes")
    assert response.status_code == HTTP_OK
    assert b"Notes" in response.data


def test_get_shopping_partial(client):
    """Test getting the shopping partial."""
    response = client.get("/partials/shopping")
    assert response.status_code == HTTP_OK
    assert b"Shopping" in response.data


def test_get_calendar_partials(client):
    """Test getting calendar partials."""
    response = client.get("/partials/calendar/week")
    assert response.status_code == HTTP_OK
    assert b"calendar-fragment" in response.data

    # Test with week offset parameter
    response = client.get("/partials/calendar/week?offset=7")  # Next week
    assert response.status_code == HTTP_OK
    assert b"calendar-fragment" in response.data

    response = client.get("/partials/calendar/week?offset=-7")  # Previous week
    assert response.status_code == HTTP_OK
    assert b"calendar-fragment" in response.data

    response = client.get("/partials/calendar/upnext")
    assert response.status_code == HTTP_OK
    assert b"upnext-list" in response.data


def test_get_weather_partial(client):
    """Test getting the weather partial."""
    response = client.get("/partials/weather")
    assert response.status_code == HTTP_OK
    assert b"Weather" in response.data


def test_weather_partial_shows_current_condition_icon(client, monkeypatch):
    """The current weather row should render the condition icon for clear sky."""

    weather_payload = {
        "current": {
            "temperature": 72,
            "feels_like": 70,
            "wind_speed": 8,
            "condition": "Clear sky",
        },
        "hourly": [
            {"time": "2026-06-07T19:00:00", "temperature": 72, "condition": "Clear sky"},
            {"time": "2026-06-07T20:00:00", "temperature": 68, "condition": "Cloudy"},
            {"time": "2026-06-07T21:00:00", "temperature": 65, "condition": "Rain"},
            {"time": "2026-06-07T22:00:00", "temperature": 64, "condition": "Clear sky"},
            {"time": "2026-06-07T23:00:00", "temperature": 62, "condition": "Clear sky"},
        ],
        "daily": [
            {"date": "2026-06-08", "high": 78, "low": 62, "condition": "Clear sky"},
            {"date": "2026-06-09", "high": 74, "low": 55, "condition": "Cloudy"},
            {"date": "2026-06-10", "high": 79, "low": 52, "condition": "Rain"},
        ],
    }
    monkeypatch.setattr("hub.routes.api.weather.get_weather_data", lambda: weather_payload)

    response = client.get("/partials/weather")

    assert response.status_code == HTTP_OK
    assert b"weather-current-condition-icon" in response.data
    assert b"Clear sky" in response.data


def test_get_shopping_tile_uses_reserved_empty_state(client, monkeypatch):
    """The dashboard tile should reserve its footprint when there are no active items."""

    done_item = ShoppingItem(id=1, text="Milk", qty="1", done=True)
    monkeypatch.setattr("hub.routes.api.shopping.list_shopping_items", lambda: [done_item])

    response = client.get("/partials/shopping?context=tile")

    assert response.status_code == HTTP_OK
    assert b"shopping-tile-body is-empty" in response.data
    assert b'data-shopping-state="empty"' in response.data


def test_calendar_partial_includes_mockup_header_controls(client):
    """Calendar header should expose the mockup-style actions."""

    response = client.get("/partials/calendar/week")

    assert response.status_code == HTTP_OK
    assert b'calendar-header-left' in response.data
    assert b'calendar-actions' in response.data
    assert b'calendar-nav-today' in response.data
    assert b'id="add-event-btn"' in response.data
    assert b'>\n                    +\n                </button>' in response.data


def test_calendar_week_partial_marks_short_events_for_readable_rendering(client, monkeypatch):
    """Short timed events should carry the compact size marker and keep title-first content."""

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    short_event = CalendarEvent(
        id=1,
        title="School Pickup",
        starts_at=now.replace(hour=19, minute=0),
        ends_at=now.replace(hour=19, minute=30),
        source="local",
    )
    monkeypatch.setattr("hub.routes.api.calendar.list_events", lambda *_args, **_kwargs: [short_event])

    response = client.get("/partials/calendar/week?view=week")
    body = response.data.decode("utf-8")

    assert response.status_code == HTTP_OK
    assert 'calendar-event-block is-short-event' in body
    assert body.index('calendar-event-block-title">School Pickup') < body.index('calendar-event-block-time')


def test_week_time_grid_collapses_exact_duplicate_timed_events():
    """Exact duplicate timed events should collapse before lane layout."""

    local_tz = ZoneInfo("America/New_York")
    start_local = datetime(2026, 6, 19, 8, 0, tzinfo=local_tz)
    end_local = datetime(2026, 6, 19, 9, 0, tzinfo=local_tz)
    date_cells = [datetime(2026, 6, 14).date() + timedelta(days=i) for i in range(7)]
    current_date = datetime(2026, 6, 19).date()

    events = [
        CalendarEvent(id=1, title="Morning appointment", starts_at=start_local, ends_at=end_local, source="google"),
        CalendarEvent(id=2, title="Morning appointment", starts_at=start_local, ends_at=end_local, source="ics"),
    ]

    time_grid = api_routes._build_week_time_grid(
        events,
        date_cells,
        current_date,
        datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
        {},
    )

    friday = next(day for day in time_grid["days"] if day["date"] == current_date)
    assert len(friday["timed_events"]) == 1


def test_week_time_grid_assigns_distinct_lanes_to_overlapping_events():
    """Overlapping timed events should split horizontally instead of fully covering one another."""

    local_tz = ZoneInfo("America/New_York")
    date_cells = [datetime(2026, 6, 14).date() + timedelta(days=i) for i in range(7)]
    target_day = datetime(2026, 6, 19).date()
    event_a = CalendarEvent(
        id=1,
        title="Morning appointment",
        starts_at=datetime(2026, 6, 19, 8, 0, tzinfo=local_tz),
        ends_at=datetime(2026, 6, 19, 9, 0, tzinfo=local_tz),
        source="google",
    )
    event_b = CalendarEvent(
        id=2,
        title="Follow-up appointment",
        starts_at=datetime(2026, 6, 19, 8, 15, tzinfo=local_tz),
        ends_at=datetime(2026, 6, 19, 8, 45, tzinfo=local_tz),
        source="google",
    )

    time_grid = api_routes._build_week_time_grid(
        [event_a, event_b],
        date_cells,
        target_day,
        datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
        {},
    )

    friday = next(day for day in time_grid["days"] if day["date"] == target_day)
    assert len(friday["timed_events"]) == 2

    first, second = friday["timed_events"]
    assert first["width_pct"] < 100
    assert second["width_pct"] < 100
    assert first["left_pct"] != second["left_pct"]


def test_week_time_grid_keeps_back_to_back_hour_events_from_overlapping():
    """Adjacent one-hour events should not visually spill into each other."""

    local_tz = ZoneInfo("America/New_York")
    date_cells = [datetime(2026, 6, 14).date() + timedelta(days=i) for i in range(7)]
    target_day = datetime(2026, 6, 19).date()
    first_event = CalendarEvent(
        id=1,
        title="Morning appointment",
        starts_at=datetime(2026, 6, 19, 8, 0, tzinfo=local_tz),
        ends_at=datetime(2026, 6, 19, 9, 0, tzinfo=local_tz),
        source="google",
    )
    second_event = CalendarEvent(
        id=2,
        title="Follow-up appointment",
        starts_at=datetime(2026, 6, 19, 9, 0, tzinfo=local_tz),
        ends_at=datetime(2026, 6, 19, 10, 0, tzinfo=local_tz),
        source="google",
    )

    time_grid = api_routes._build_week_time_grid(
        [first_event, second_event],
        date_cells,
        target_day,
        datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
        {},
    )

    friday = next(day for day in time_grid["days"] if day["date"] == target_day)
    first, second = friday["timed_events"]
    assert first["left_pct"] == 0
    assert second["left_pct"] == 0
    assert first["width_pct"] == 100
    assert second["width_pct"] == 100
    assert first["top_pct"] + first["height_pct"] <= second["top_pct"]


def test_week_time_grid_places_single_day_all_day_event_on_correct_day():
    """Exclusive-end all-day events should appear on their intended local day."""

    local_tz = ZoneInfo("America/New_York")
    date_cells = [datetime(2026, 6, 14).date() + timedelta(days=i) for i in range(7)]
    ooo_event = CalendarEvent(
        id=1,
        title="Cole OOO - Juneteenth",
        starts_at=datetime(2026, 6, 19, 0, 0, tzinfo=local_tz),
        ends_at=datetime(2026, 6, 20, 0, 0, tzinfo=local_tz),
        all_day=True,
        owner="person@example.com",
        source="google",
    )

    time_grid = api_routes._build_week_time_grid(
        [ooo_event],
        date_cells,
        datetime(2026, 6, 19).date(),
        datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
        {},
    )

    assert len(time_grid["all_day_rows"]) == 1
    placement = time_grid["all_day_rows"][0]
    assert placement["start_col"] == 5
    assert placement["span_cols"] == 1


def test_week_time_grid_places_google_style_all_day_event_on_correct_day():
    """Google date-only all-day events normalized to UTC should still land on the intended day."""

    date_cells = [datetime(2026, 6, 14).date() + timedelta(days=i) for i in range(7)]
    google_style_event = CalendarEvent(
        id=1,
        title="Cole OOO - Juneteenth",
        starts_at=datetime(2026, 6, 19, 0, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 20, 0, 0, tzinfo=timezone.utc),
        all_day=True,
        owner="person@example.com",
        source="google",
    )

    time_grid = api_routes._build_week_time_grid(
        [google_style_event],
        date_cells,
        datetime(2026, 6, 19).date(),
        datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
        {},
    )

    placement = time_grid["all_day_rows"][0]
    assert placement["start_col"] == 5
    assert placement["span_cols"] == 1


def test_week_time_grid_spans_multi_day_all_day_events_and_stacks_conflicts():
    """Multi-day all-day events should span columns and conflicting bars should stack."""

    local_tz = ZoneInfo("America/New_York")
    date_cells = [datetime(2026, 6, 14).date() + timedelta(days=i) for i in range(7)]
    first = CalendarEvent(
        id=1,
        title="Cole OOO",
        starts_at=datetime(2026, 6, 19, 0, 0, tzinfo=local_tz),
        ends_at=datetime(2026, 6, 21, 0, 0, tzinfo=local_tz),
        all_day=True,
        source="google",
    )
    second = CalendarEvent(
        id=2,
        title="Family Trip",
        starts_at=datetime(2026, 6, 20, 0, 0, tzinfo=local_tz),
        ends_at=datetime(2026, 6, 22, 0, 0, tzinfo=local_tz),
        all_day=True,
        source="google",
    )

    time_grid = api_routes._build_week_time_grid(
        [first, second],
        date_cells,
        datetime(2026, 6, 19).date(),
        datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
        {},
    )

    assert time_grid["all_day_row_count"] == 2
    placements = {item["event"].title: item for item in time_grid["all_day_rows"]}
    assert placements["Cole OOO"]["start_col"] == 5
    assert placements["Cole OOO"]["span_cols"] == 2
    assert placements["Family Trip"]["start_col"] == 6
    assert placements["Family Trip"]["span_cols"] == 1
    assert placements["Cole OOO"]["row_index"] != placements["Family Trip"]["row_index"]


def test_group_events_by_date_for_template_collapses_exact_duplicates():
    """Month view grouping should collapse exact duplicates but keep distinct events."""

    local_tz = ZoneInfo("America/New_York")
    target_date = datetime(2026, 6, 19).date()
    duplicate_a = CalendarEvent(
        id=1,
        title="Morning appointment",
        starts_at=datetime(2026, 6, 19, 8, 0, tzinfo=local_tz),
        ends_at=datetime(2026, 6, 19, 9, 0, tzinfo=local_tz),
        source="google",
    )
    duplicate_b = CalendarEvent(
        id=2,
        title="Morning appointment",
        starts_at=datetime(2026, 6, 19, 8, 0, tzinfo=local_tz),
        ends_at=datetime(2026, 6, 19, 9, 0, tzinfo=local_tz),
        source="ics",
    )
    distinct = CalendarEvent(
        id=3,
        title="Follow-up appointment",
        starts_at=datetime(2026, 6, 19, 8, 15, tzinfo=local_tz),
        ends_at=datetime(2026, 6, 19, 8, 45, tzinfo=local_tz),
        source="google",
    )

    grouped = group_events_by_date_for_template([duplicate_a, duplicate_b, distinct], target_date)

    assert [event.title for event in grouped] == ["Morning appointment", "Follow-up appointment"]


def test_calendar_week_partial_renders_overlap_lanes_and_spanning_all_day_bar(client, monkeypatch):
    """Rendered week view should expose overlap lane styles and all-day spanning metadata."""

    local_tz = ZoneInfo("America/New_York")
    events = [
        CalendarEvent(
            id=1,
            title="Cole OOO - Juneteenth",
            starts_at=datetime(2026, 6, 19, 0, 0, tzinfo=local_tz),
            ends_at=datetime(2026, 6, 20, 0, 0, tzinfo=local_tz),
            all_day=True,
            owner="person@example.com",
            source="google",
        ),
        CalendarEvent(
            id=2,
            title="Morning appointment",
            starts_at=datetime(2026, 6, 19, 8, 0, tzinfo=local_tz),
            ends_at=datetime(2026, 6, 19, 9, 0, tzinfo=local_tz),
            source="google",
        ),
        CalendarEvent(
            id=3,
            title="Follow-up appointment",
            starts_at=datetime(2026, 6, 19, 8, 15, tzinfo=local_tz),
            ends_at=datetime(2026, 6, 19, 8, 45, tzinfo=local_tz),
            source="google",
        ),
    ]
    monkeypatch.setattr("hub.routes.api.calendar.list_events", lambda *_args, **_kwargs: events)
    client.application.config["CONFIG"].family = [
        {"name": "Person", "emails": ["person@example.com"], "color": "#2ecc71"}
    ]

    offset = (datetime(2026, 6, 19).date() - datetime.now().date()).days
    response = client.get(f"/partials/calendar/week?view=week&offset={offset}")
    body = response.data.decode("utf-8")

    assert response.status_code == HTTP_OK
    assert 'calendar-allday-row' in body
    assert 'calendar-allday-track' in body
    assert 'calendar-allday-bar has-owner' in body
    assert 'grid-column:' in body and '/ span 1' in body
    assert 'left: ' in body
    assert 'width: ' in body


def test_calendar_week_partial_renders_one_time_row_per_hour(client, monkeypatch):
    """Week view should render one body row per displayed hour, not one per axis label."""

    local_tz = ZoneInfo("America/New_York")
    events = [
        CalendarEvent(
            id=1,
            title="Trach night",
            starts_at=datetime(2026, 6, 16, 19, 0, tzinfo=local_tz),
            ends_at=datetime(2026, 6, 16, 20, 0, tzinfo=local_tz),
            source="google",
        )
    ]
    monkeypatch.setattr("hub.routes.api.calendar.list_events", lambda *_args, **_kwargs: events)
    client.application.config["CONFIG"].family = [
        {"name": "Person", "emails": ["person@example.com"], "color": "#2ecc71"}
    ]

    response = client.get("/partials/calendar/week?view=week")
    body = response.data.decode("utf-8")

    assert response.status_code == HTTP_OK
    expected_row_count = 7 * 12  # 7 days * default 8 AM to 8 PM hour blocks
    assert body.count('class="calendar-hour-row"') == expected_row_count
    assert body.count('class="calendar-hour-label"') == 12
    assert 'class="calendar-hour-label calendar-hour-label-end">8 PM<' in body


def test_get_miniplayer_partial_shows_compact_source_controls(client):
    """Sidebar miniplayer should expose the compact source controls and placeholder sources."""

    response = client.get("/partials/miniplayer")

    assert response.status_code == HTTP_OK
    assert b"miniplayer-source-pills" in response.data
    assert b"Spotify" in response.data
    assert b"Podcasts" in response.data
    assert b"FM Radio" in response.data
    assert b"spotify-shuffle-btn" in response.data
    assert b"miniplayer-device-select" in response.data
    assert b"spotify-playlist-list" in response.data
    assert b"spotify-playlist-empty" in response.data


def test_get_media_partial(client):
    """Test getting the media partial."""
    response = client.get("/partials/media")
    assert response.status_code == HTTP_OK
    assert b"Media" in response.data


def test_health_endpoint(client):
    """Test the health endpoint."""
    response = client.get("/health")
    assert response.status_code == HTTP_OK
    data = response.get_json()
    assert "status" in data
    assert data["status"] == "ok"


def test_post_note(client):
    """Test creating a note via API."""
    response = client.post("/api/notes", json={"text": "Test note"}, content_type="application/json")
    assert response.status_code == HTTP_CREATED
    data = response.get_json()
    assert "id" in data
    assert data["text"] == "Test note"


def test_post_shopping_item(client):
    """Test creating a shopping item via API."""
    response = client.post("/api/shopping", json={"text": "Milk", "qty": "1 gallon"}, content_type="application/json")
    assert response.status_code == HTTP_CREATED
    data = response.get_json()
    assert "id" in data
    assert data["text"] == "Milk"


def test_launch_app(client):
    """Test launching an app via API."""
    response = client.post("/api/launch", json={"app_id": "calendar"}, content_type="application/json")
    # This might return different status based on config availability
    # Just test that it returns some response
    assert response.status_code in [HTTP_OK, HTTP_BAD_REQUEST]


def test_post_calendar_event(client):
    """Test creating a calendar event via API."""

    starts_at = datetime.now(timezone.utc).isoformat()
    ends_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    event_data = {"title": "Test Event", "starts_at": starts_at, "ends_at": ends_at, "location": "Test Location"}

    response = client.post("/api/calendar/local", data=json.dumps(event_data), content_type="application/json")

    # The response might vary depending on whether the datetime format is accepted
    assert response.status_code in [HTTP_CREATED, HTTP_BAD_REQUEST]


def test_get_root(client):
    """Test getting the root page."""
    response = client.get("/")
    assert response.status_code == HTTP_OK
    assert b"Kitchen Hub" in response.data


def test_ingredients_to_shopping(client):
    """Test adding ingredients to shopping list via API."""
    response = client.post("/api/ingredients-to-shopping", content_type="application/json")
    assert response.status_code == HTTP_OK
    assert b"ingredients to shopping list" in response.data
