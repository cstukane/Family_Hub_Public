import os
import platform
import re
from datetime import datetime, timedelta, timezone
from typing import List, Union
from zoneinfo import ZoneInfo

import requests as _requests
from flask import current_app, jsonify, make_response, redirect, render_template, request
from google_auth_oauthlib.flow import Flow

from hub import __version__
from hub.adapters.homeassistant import initialize_ha_adapter
from hub.services import calendar, media, notes, shopping, sports, timers, voice, weather
from hub.utils.auth import generate_media_launcher_token
from hub.utils.config_helpers import get_config_dict
from hub.utils.decorators import require_admin_rate_limit, require_default_rate_limit, require_ip_whitelist
from hub.utils.validation import validate_request_json

from . import api_bp


@api_bp.before_request
def _validate_api_request():
    """Apply basic payload validation to all API endpoints."""
    return validate_request_json()


def _safe_int(raw_value, default=0):
    """Convert raw value to int, returning default on failure."""
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default


def _format_weather_status_text(weather_data: dict, include_prefix: bool = False) -> str:
    """Format weather freshness text from a weather service payload."""
    prefix = "Weather " if include_prefix else ""
    if not isinstance(weather_data, dict) or weather_data.get("error"):
        error_message = weather_data.get("error") if isinstance(weather_data, dict) else "Weather data unavailable"
        return f"Weather unavailable: {error_message}"

    if "last_updated" not in weather_data:
        return f"{prefix}updated: Unknown".strip()

    last_updated = datetime.fromisoformat(weather_data["last_updated"].replace("Z", "+00:00"))
    time_diff = datetime.now(timezone.utc) - last_updated
    minutes_ago = int(time_diff.total_seconds() // 60)

    if minutes_ago < 1:
        return f"{prefix}updated just now".strip()
    if minutes_ago == 1:
        return f"{prefix}updated 1 minute ago".strip()
    return f"{prefix}updated {minutes_ago} minutes ago".strip()


def _format_calendar_status_text(status_info: dict) -> str:
    """Format calendar status text from the calendar service payload."""
    status_message = status_info.get("status", "Calendar status unknown")
    refresh_interval = status_info.get("refresh_interval", "")
    if refresh_interval:
        return f"Calendar: {status_message}, refreshing every {refresh_interval}"
    return f"Calendar: {status_message}"


def _build_rrule(
    starts_at: datetime,
    repeat: str,
    repeat_end: str,
    repeat_count: int,
    repeat_until: str,
) -> list:
    """Build a basic Google RRULE list from repeat settings."""
    if not repeat or repeat == "none":
        return []

    freq_map = {
        "daily": "DAILY",
        "weekly": "WEEKLY",
        "monthly": "MONTHLY",
        "yearly": "YEARLY",
    }
    freq = freq_map.get(repeat)
    if not freq:
        return []

    rule = f"RRULE:FREQ={freq}"

    if repeat_end == "count" and repeat_count > 0:
        rule += f";COUNT={repeat_count}"
    elif repeat_end == "until" and repeat_until:
        try:
            until_dt = datetime.fromisoformat(repeat_until)
            if until_dt.tzinfo is None:
                tzinfo = starts_at.tzinfo or timezone.utc
                until_dt = datetime(
                    until_dt.year,
                    until_dt.month,
                    until_dt.day,
                    23,
                    59,
                    59,
                    tzinfo=tzinfo,
                )
            until_utc = until_dt.astimezone(timezone.utc)
            rule += f";UNTIL={until_utc.strftime('%Y%m%dT%H%M%SZ')}"
        except ValueError:
            pass

    return [rule]


def _get_week_start(date_obj: datetime, start_on_monday: bool = False) -> datetime:
    """Return the start of the week for the given date (Sunday or Monday start)."""
    if start_on_monday:
        days_to_subtract = date_obj.weekday()
    else:
        days_to_subtract = (date_obj.weekday() + 1) % 7  # Sunday = 0 offset
    return date_obj.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_to_subtract)


def _shift_month(start_date: datetime, month_delta: int) -> datetime:
    """Shift a date (assumed day=1) by a number of months without using external deps."""
    total_months = start_date.month - 1 + month_delta
    year = start_date.year + total_months // 12
    month = total_months % 12 + 1
    return start_date.replace(year=year, month=month)


def _build_calendar_view_context(view_mode: str, offset_days: int = 0, month_offset: int = 0) -> dict:
    """Build calendar context for week, workweek, or month view."""
    view_mode_normalized = (view_mode or "week").lower()
    if view_mode_normalized not in {"week", "workweek", "month"}:
        view_mode_normalized = "week"

    today = datetime.now()
    current_date = today.date()
    headers = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    context = {
        "view_mode": view_mode_normalized,
        "current_date": current_date,
        "current_hour": today.hour,
        "current_minute": today.minute,
        "offset_days": offset_days,
        "month_offset": month_offset,
    }

    if view_mode_normalized == "workweek":
        start_of_week = _get_week_start(today, start_on_monday=True) + timedelta(days=offset_days)
        end_of_week = start_of_week + timedelta(days=4)
        date_cells = [(start_of_week + timedelta(days=i)).date() for i in range(5)]

        context.update(
            {
                "range_start": start_of_week,
                "range_end": end_of_week,
                "range_label": f"Work week: {start_of_week:%b %d} - {end_of_week:%b %d, %Y}",
                "month_year_label": end_of_week.strftime("%B %Y"),
                "headers": headers[1:6],
                "date_cells": date_cells,
                "nav_previous": offset_days - 7,
                "nav_next": offset_days + 7,
                "aria_label": "Work week calendar grid",
            }
        )
    elif view_mode_normalized == "month":
        base_month = _shift_month(today.replace(day=1, hour=0, minute=0, second=0, microsecond=0), month_offset)
        month_reference = base_month.date()

        grid_start = _get_week_start(base_month, start_on_monday=False)

        if base_month.month == 12:
            next_month = base_month.replace(year=base_month.year + 1, month=1)
        else:
            next_month = base_month.replace(month=base_month.month + 1)
        last_of_month = next_month - timedelta(days=1)
        end_padding = 6 - ((last_of_month.weekday() + 1) % 7)
        grid_end = last_of_month + timedelta(days=end_padding)

        total_days = (grid_end - grid_start).days + 1
        date_cells = [(grid_start + timedelta(days=i)).date() for i in range(total_days)]

        context.update(
            {
                "range_start": grid_start,
                "range_end": grid_end,
                "range_label": base_month.strftime("%B %Y"),
                "month_year_label": base_month.strftime("%B %Y"),
                "headers": headers,
                "date_cells": date_cells,
                "nav_previous": month_offset - 1,
                "nav_next": month_offset + 1,
                "month_reference": month_reference,
                "aria_label": "Monthly calendar grid",
            }
        )
    else:
        start_of_week = _get_week_start(today, start_on_monday=False) + timedelta(days=offset_days)
        end_of_week = start_of_week + timedelta(days=6)
        date_cells = [(start_of_week + timedelta(days=i)).date() for i in range(7)]

        context.update(
            {
                "range_start": start_of_week,
                "range_end": end_of_week,
                "range_label": f"Week of {start_of_week:%b %d} - {end_of_week:%b %d, %Y}",
                "month_year_label": end_of_week.strftime("%B %Y"),
                "headers": headers,
                "date_cells": date_cells,
                "nav_previous": offset_days - 7,
                "nav_next": offset_days + 7,
                "aria_label": "Weekly calendar grid",
            }
        )

    return context


_GRID_TZ = ZoneInfo("America/New_York")
_MIN_GRID_SPAN_HOURS = 8
_DEFAULT_GRID_START_HOUR = 8
_DEFAULT_GRID_END_HOUR = 20


def _resolve_owner_color(event, config_dict):
    """Resolve the family-member color associated with an event's owner."""
    owner = str(event.owner) if getattr(event, "owner", None) else ""
    if config_dict and config_dict.get("family"):
        for member in config_dict["family"]:
            member_emails = member.get("emails") or []
            if member.get("name") == owner or (owner and owner in member_emails):
                return member.get("color")
    return None


def _to_grid_local(dt):
    """Convert a datetime to the calendar grid's display timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_GRID_TZ)


def _normalize_event_title(title):
    """Normalize titles for display-level deduplication."""
    return re.sub(r"\s+", " ", (title or "").strip()).casefold()


def _event_display_key(event, start_local, end_local):
    """Build a local-time dedupe key for calendar display surfaces."""
    return (
        bool(getattr(event, "all_day", False)),
        _normalize_event_title(getattr(event, "title", "")),
        start_local.isoformat() if start_local else None,
        end_local.isoformat() if end_local else None,
    )


def _all_day_display_dates(event):
    """Return display dates for all-day events using date semantics, not local-midnight conversion."""
    if not getattr(event, "starts_at", None):
        return None, None

    start_dt = event.starts_at
    end_dt = event.ends_at or start_dt
    start_date = start_dt.date()

    if end_dt <= start_dt:
        end_date = start_date
    elif end_dt.time() == datetime.min.time():
        end_date = (end_dt - timedelta(days=1)).date()
    else:
        end_date = end_dt.date()

    return start_date, end_date


def _dedupe_display_events(events_with_times):
    """Collapse exact duplicate events for display without mutating source data."""
    seen = set()
    deduped = []
    for item in events_with_times:
        key = _event_display_key(item["event"], item["start"], item["end"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _build_week_time_grid(events, date_cells, current_date, now, config_dict):
    """Compute hour-axis layout data for the week/workweek time-grid calendar view.

    Returns a dict with the visible hour range, hour-axis labels, a "now" line
    position (for today's column, if visible), and per-day all-day/timed event
    lists with pre-computed top/height percentages for absolute positioning.
    """
    day_buckets = {day: {"timed": []} for day in date_cells}
    all_day_spans = []
    timed_starts = []
    timed_ends = []
    day_index_map = {day: index for index, day in enumerate(date_cells)}

    for event in events:
        start_local = _to_grid_local(event.starts_at)
        if start_local is None:
            continue

        owner_color = _resolve_owner_color(event, config_dict)
        end_local = _to_grid_local(event.ends_at) or start_local
        if getattr(event, "all_day", False):
            dedupe_item = {"event": event, "owner_color": owner_color, "start": start_local, "end": end_local}
            all_day_spans.append(dedupe_item)
            continue

        event_date = start_local.date()
        if event_date not in day_buckets:
            continue
        day_buckets[event_date]["timed"].append(
            {"event": event, "owner_color": owner_color, "start": start_local, "end": end_local}
        )
        timed_starts.append(start_local)
        timed_ends.append(end_local)

    if timed_starts:
        earliest, latest = min(timed_starts), max(timed_ends)
        grid_start_hour = min(earliest.hour, _DEFAULT_GRID_START_HOUR)
        grid_end_hour = max(latest.hour + (1 if latest.minute else 0), _DEFAULT_GRID_END_HOUR)
        if grid_end_hour - grid_start_hour < _MIN_GRID_SPAN_HOURS:
            grid_end_hour = grid_start_hour + _MIN_GRID_SPAN_HOURS
    else:
        grid_start_hour, grid_end_hour = _DEFAULT_GRID_START_HOUR, _DEFAULT_GRID_END_HOUR

    grid_end_hour = min(grid_end_hour, 24)
    total_minutes = (grid_end_hour - grid_start_hour) * 60

    hour_labels = []
    for hour in range(grid_start_hour, grid_end_hour + 1):
        label_hour = hour % 24
        suffix = "AM" if label_hour < 12 else "PM"
        display_hour = label_hour % 12 or 12
        hour_labels.append(f"{display_hour} {suffix}")

    def _layout(start, end):
        start_minutes = (start.hour - grid_start_hour) * 60 + start.minute
        end_minutes = (end.hour - grid_start_hour) * 60 + end.minute
        if end_minutes <= start_minutes:
            end_minutes = start_minutes + 30
        top_pct = max(0.0, min(100.0, start_minutes / total_minutes * 100))
        duration_minutes = max(1, end_minutes - start_minutes)
        raw_height_pct = (duration_minutes / total_minutes) * 100
        if duration_minutes <= 30:
            size_class = "is-short-event"
        elif duration_minutes <= 60:
            size_class = "is-medium-event"
        else:
            size_class = "is-long-event"
        height_pct = min(100.0 - top_pct, raw_height_pct)
        return round(top_pct, 2), round(height_pct, 2), size_class

    now_local = _to_grid_local(now)
    now_top_pct = None
    now_day_index = None
    all_day_rows = []
    all_day_row_count = 0

    def _build_all_day_placements(items):
        placements = []
        visible_rows = []
        for item in _dedupe_display_events(items):
            start_date, inclusive_end_date = _all_day_display_dates(item["event"])
            if start_date is None or inclusive_end_date is None:
                continue

            visible_start = max(start_date, date_cells[0])
            visible_end = min(inclusive_end_date, date_cells[-1])
            if visible_start > visible_end:
                continue

            start_col = day_index_map[visible_start]
            end_col = day_index_map[visible_end]
            placements.append(
                {
                    "event": item["event"],
                    "owner_color": item["owner_color"],
                    "start_col": start_col,
                    "end_col": end_col,
                    "span_cols": (end_col - start_col) + 1,
                }
            )

        placements.sort(key=lambda placement: (placement["start_col"], placement["end_col"], placement["event"].title))
        for placement in placements:
            row_index = 0
            while row_index < len(visible_rows) and placement["start_col"] <= visible_rows[row_index]:
                row_index += 1
            if row_index == len(visible_rows):
                visible_rows.append(placement["end_col"])
            else:
                visible_rows[row_index] = placement["end_col"]
            placement["row_index"] = row_index

        return placements, len(visible_rows)

    def _assign_timed_layout(items):
        if not items:
            return []

        deduped_items = _dedupe_display_events(items)
        deduped_items.sort(key=lambda i: (i["start"], i["end"], i["event"].title))

        clusters = []
        current_cluster = []
        current_cluster_end = None
        for item in deduped_items:
            if not current_cluster or item["start"] < current_cluster_end:
                current_cluster.append(item)
                current_cluster_end = max(current_cluster_end, item["end"]) if current_cluster_end else item["end"]
            else:
                clusters.append(current_cluster)
                current_cluster = [item]
                current_cluster_end = item["end"]
        if current_cluster:
            clusters.append(current_cluster)

        laid_out = []
        for cluster in clusters:
            lane_ends = []
            cluster_layout = []
            for item in cluster:
                lane_index = None
                for index, lane_end in enumerate(lane_ends):
                    if item["start"] >= lane_end:
                        lane_index = index
                        lane_ends[index] = item["end"]
                        break
                if lane_index is None:
                    lane_index = len(lane_ends)
                    lane_ends.append(item["end"])
                cluster_layout.append((item, lane_index))

            lane_count = max(1, len(lane_ends))
            lane_width = round(100.0 / lane_count, 2)
            for item, lane_index in cluster_layout:
                top_pct, height_pct, size_class = _layout(item["start"], item["end"])
                laid_out.append(
                    {
                        "event": item["event"],
                        "owner_color": item["owner_color"],
                        "top_pct": top_pct,
                        "height_pct": height_pct,
                        "left_pct": round(lane_width * lane_index, 2),
                        "width_pct": lane_width,
                        "size_class": size_class,
                    }
                )

        return laid_out

    all_day_rows, all_day_row_count = _build_all_day_placements(all_day_spans)

    days = []
    for index, day in enumerate(date_cells):
        bucket = day_buckets[day]
        timed_events = _assign_timed_layout(bucket["timed"])

        is_today = day == current_date
        days.append(
            {
                "date": day,
                "is_today": is_today,
                "timed_events": timed_events,
            }
        )

        if now_local and is_today and day == now_local.date():
            now_minutes = (now_local.hour - grid_start_hour) * 60 + now_local.minute
            if 0 <= now_minutes <= total_minutes:
                now_top_pct = round(now_minutes / total_minutes * 100, 2)
                now_day_index = index

    return {
        "grid_start_hour": grid_start_hour,
        "grid_end_hour": grid_end_hour,
        "grid_row_count": grid_end_hour - grid_start_hour,
        "hour_labels": hour_labels,
        "now_top_pct": now_top_pct,
        "now_day_index": now_day_index,
        "all_day_rows": all_day_rows,
        "all_day_row_count": all_day_row_count,
        "days": days,
    }


@api_bp.route("/api/notes", methods=["GET"])
@require_default_rate_limit
def get_all_notes():
    """Get all notes."""
    all_notes = notes.list_notes()
    return jsonify([note.to_dict() for note in all_notes])


@api_bp.route("/api/notes", methods=["POST"])
@require_default_rate_limit
def create_note():
    """Create a new note."""
    data = request.get_json(silent=True) or {}
    if not data and request.form:
        data = request.form.to_dict()

    text = (data.get("text") or "").strip()

    if not text:
        return jsonify({"error": "Text is required"}), 400

    note = notes.create_note(text)
    if request.headers.get("HX-Request"):
        response_html = render_template("partials/_note_modal_item.html", note=note)
        response = make_response(response_html, 201)
        response.headers["HX-Trigger"] = "refreshSidebarCounts"
        return response

    return jsonify(note.to_dict()), 201


@api_bp.route("/api/notes/<int:id>", methods=["GET"])
@require_default_rate_limit
def get_note(id):
    """Get a specific note."""
    note = notes.get_note(id)
    if not note:
        return jsonify({"error": "Note not found"}), 404
    return jsonify(note.to_dict()), 200


@api_bp.route("/api/notes/<int:id>/edit", methods=["GET"])
@require_default_rate_limit
def get_note_edit_form(id):
    """Get the edit form for a specific note."""
    note = notes.get_note(id)
    if not note:
        return jsonify({"error": "Note not found"}), 404

    # Render the edit form as HTML
    form_html = f"""
    <li class="list-group-item" id="note-{note.id}">
        <form hx-put="/api/notes/{note.id}" hx-target="#note-{note.id}" hx-swap="outerHTML">
            <div class="form-group">
                <textarea name="text" class="form-control" required>{note.text}</textarea>
            </div>
            <div class="note-actions">
                <button type="submit" class="btn btn-sm">Save</button>
                <button type="button" class="btn btn-sm"
                        hx-get="/partials/notes"
                        hx-target="#notes-list"
                        hx-swap="innerHTML">
                    Cancel
                </button>
            </div>
        </form>
    </li>
    """
    return form_html


@api_bp.route("/api/notes/<int:id>", methods=["PUT"])
@require_admin_rate_limit
def update_note(id):
    """Update a note."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")

    if not text.strip():
        return jsonify({"error": "Text is required"}), 400

    note = notes.update_note(id, text)
    if not note:
        return jsonify({"error": "Note not found"}), 404
    return jsonify(note.to_dict()), 200


@api_bp.route("/api/notes/<int:id>", methods=["DELETE"])
@require_admin_rate_limit
def delete_note(id):
    """Delete a note."""
    success = notes.delete_note(id)
    if not success:
        return jsonify({"error": "Note not found"}), 404

    if request.headers.get("HX-Request"):
        response = make_response(jsonify({"status": "deleted"}), 200)
        response.headers["HX-Trigger"] = "refreshSidebarCounts"
        return response

    return jsonify({"status": "deleted"}), 200


@api_bp.route("/api/shopping", methods=["GET"])
@require_default_rate_limit
def get_all_shopping_items():
    """Get all shopping items."""
    all_items = shopping.list_shopping_items()
    return jsonify([item.to_dict() for item in all_items])


@api_bp.route("/api/shopping", methods=["POST"])
@require_default_rate_limit
def create_shopping_item():
    """Create a new shopping item."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    qty = data.get("qty")

    if not text.strip():
        return jsonify({"error": "Text is required"}), 400

    item = shopping.create_shopping_item(text, qty)
    if request.headers.get("HX-Request"):
        response = make_response(jsonify(item.to_dict()), 201)
        response.headers["HX-Trigger"] = "refreshSidebarCounts"
        return response

    return jsonify(item.to_dict()), 201


@api_bp.route("/api/shopping/<int:id>", methods=["GET"])
def get_shopping_item(id):
    """Get a specific shopping item."""
    item = shopping.get_shopping_item(id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item.to_dict()), 200


@api_bp.route("/api/shopping/<int:id>/edit", methods=["GET"])
def get_shopping_item_edit_form(id):
    """Get the edit form for a specific shopping item."""
    item = shopping.get_shopping_item(id)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    # Render the edit form as HTML
    form_html = f'''
    <li class="list-group-item" id="item-{item.id}">
        <form hx-put="/api/shopping/{item.id}" hx-target="#item-{item.id}" hx-swap="outerHTML">
            <div class="d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center">
                    <input type="checkbox" name="done" class="shopping-checkbox" {"checked" if item.done else ""}>
                    <input type="text" name="qty" class="form-control"
               value="{item.qty or ""}" placeholder="Qty"
               style="width: 60px; margin: 0 5px;">
                    <input type="text" name="text" class="form-control"
                           value="{item.text}" required style="flex: 1; margin-right: 10px;">
                </div>
                <div class="shopping-actions">
                    <button type="submit" class="btn btn-sm">Save</button>
                    <button type="button" class="btn btn-sm"
                            hx-get="/partials/shopping"
                            hx-target="#shopping-list"
                            hx-swap="innerHTML">
                        Cancel
                    </button>
                </div>
            </div>
        </form>
    </li>
    '''
    return form_html


@api_bp.route("/api/shopping/<int:id>", methods=["PUT"])
@require_admin_rate_limit
def update_shopping_item(id):
    """Update a shopping item."""
    data = request.get_json(silent=True) or {}
    text = data.get("text")
    done = data.get("done")
    qty = data.get("qty")

    item = shopping.update_shopping_item(id, text, done, qty)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item.to_dict()), 200


@api_bp.route("/api/shopping/<int:id>", methods=["PATCH"])
def patch_shopping_item(id):
    """Partially update a shopping item (toggle done, change qty, etc.)."""
    data = request.get_json(silent=True) or {}
    text = data.get("text")
    done = data.get("done")
    qty = data.get("qty")

    item = shopping.update_shopping_item(id, text, done, qty)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item.to_dict()), 200


@api_bp.route("/api/shopping/<int:id>/toggle", methods=["POST"])
def toggle_shopping_item(id):
    """Toggle the done status of a shopping item."""
    item = shopping.toggle_shopping_item_done(id)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    if request.headers.get("HX-Request"):
        response = make_response(jsonify(item.to_dict()), 200)
        response.headers["HX-Trigger"] = "refreshSidebarCounts"
        return response

    return jsonify(item.to_dict()), 200


@api_bp.route("/api/shopping/<int:id>", methods=["DELETE"])
def delete_shopping_item(id):
    """Delete a shopping item."""
    success = shopping.delete_shopping_item(id)
    if not success:
        return jsonify({"error": "Item not found"}), 404

    if request.headers.get("HX-Request"):
        response = make_response(jsonify({"status": "deleted"}), 200)
        response.headers["HX-Trigger"] = "refreshSidebarCounts"
        return response

    return jsonify({"status": "deleted"}), 200


@api_bp.route("/api/shopping", methods=["DELETE"])
@require_admin_rate_limit
def clear_all_shopping_items():
    """Clear all shopping items."""
    all_items = shopping.list_shopping_items()

    for item in all_items:
        shopping.delete_shopping_item(item.id)

    return jsonify({"status": "all deleted", "count": len(all_items)}), 200


@api_bp.route("/api/shopping/clear-all", methods=["POST"])
@require_admin_rate_limit
def clear_all_shopping_items_post():
    """Clear all shopping items (POST version for HTMX)."""
    all_items = shopping.list_shopping_items()

    for item in all_items:
        shopping.delete_shopping_item(item.id)

    return jsonify({"status": "all deleted", "count": len(all_items)}), 200


@api_bp.route("/api/calendar/local", methods=["POST"])
@require_admin_rate_limit
def create_calendar_event():
    """Create a calendar event (local database or Google Calendar)."""
    data = request.get_json(silent=True) or {} or {}

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    starts_at_str = data.get("starts_at", "")
    ends_at_str = data.get("ends_at")
    location = (data.get("location") or "").strip() or None
    description = (data.get("description") or "").strip() or None
    visibility = (data.get("visibility") or "").strip() or None
    color = (data.get("color") or "").strip() or None

    raw_all_day = data.get("all_day", False)
    if isinstance(raw_all_day, str):
        all_day = raw_all_day.lower() in {"1", "true", "yes", "on"}
    else:
        all_day = bool(raw_all_day)

    calendar_selection = data.get("calendar_selection")
    calendar_type = data.get("calendar_type")
    calendar_id = data.get("calendar_id")

    if not calendar_type and calendar_selection:
        if calendar_selection.startswith("google:"):
            calendar_type = "google"
            calendar_id = calendar_selection.split(":", 1)[1] or "primary"
        else:
            calendar_type = "local"
    elif not calendar_type:
        for option in calendar.get_configured_calendar_options():
            value = option.get("value") if isinstance(option, dict) else None
            if value and value.startswith("google:"):
                calendar_type = "google"
                calendar_id = value.split(":", 1)[1] or "primary"
                break

    calendar_type = calendar_type or "local"
    if calendar_type == "local":
        calendar_id = "local"
    elif calendar_type == "google" and not calendar_id:
        calendar_id = "primary"

    guests = data.get("guests") or []
    if isinstance(guests, str):
        guests = [email.strip() for email in guests.replace(";", ",").split(",") if email.strip()]
    elif isinstance(guests, list):
        guests = [str(email).strip() for email in guests if str(email).strip()]
    else:
        guests = []

    reminders_raw = data.get("reminders")
    reminders: List[Union[str, int]] = []
    if isinstance(reminders_raw, list):
        for reminder in reminders_raw:
            value = str(reminder).strip()
            if value:
                reminders.append(value)
    elif reminders_raw is not None:
        value = str(reminders_raw).strip()
        if value:
            reminders.append(value)

    repeat = (data.get("repeat") or "").strip()
    repeat_end = (data.get("repeat_end") or "never").strip()
    repeat_count = _safe_int(data.get("repeat_count"), 0)
    repeat_until = (data.get("repeat_until") or "").strip()

    def _parse_datetime(value: str) -> datetime:
        if not value:
            raise ValueError("Missing date value")
        # Replace trailing Z with UTC offset for compatibility
        cleaned = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt

    try:
        starts_at = _parse_datetime(starts_at_str)
        if ends_at_str:
            ends_at = _parse_datetime(ends_at_str)
        else:
            ends_at = starts_at + timedelta(hours=1)
        if ends_at <= starts_at:
            ends_at = starts_at + timedelta(hours=1)

        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)

        recurrence = _build_rrule(starts_at, repeat, repeat_end, repeat_count, repeat_until)

        if calendar_type == "google":
            event = calendar.add_google_calendar_event(
                title,
                starts_at,
                ends_at,
                location=location,
                description=description,
                all_day=all_day,
                calendar_id=calendar_id,
                guests=guests,
                reminders=reminders,
                visibility=visibility,
                color=color,
                recurrence=recurrence or None,
            )
            if not event:
                return jsonify({"error": "Failed to create event in Google Calendar"}), 500
        else:
            event = calendar.add_event(
                title,
                starts_at,
                ends_at,
                location=location,
                description=description,
                all_day=all_day,
                visibility=visibility,
                color=color,
                calendar_id=calendar_id,
                guests=guests,
                reminders=reminders,
            )

        return jsonify(event.to_dict()), 201
    except ValueError as e:
        return jsonify({"error": f"Invalid date format: {e}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/media/open", methods=["POST"])
@require_default_rate_limit
def media_open_proxy():
    """Proxy media-open requests to the local launcher service to avoid browser CORS."""
    config = current_app.config.get("CONFIG")
    launcher_endpoint = "http://127.0.0.1:7666/v1/open_media"
    if config and hasattr(config, "media") and config.media:
        launcher_endpoint = getattr(config.media, "launcher_endpoint", launcher_endpoint)

    data = request.get_json(silent=True) or {}
    token = generate_media_launcher_token(ttl_seconds=60)
    try:
        resp = _requests.post(
            launcher_endpoint,
            json=data,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=5,
        )
        return jsonify(resp.json()), resp.status_code
    except _requests.exceptions.ConnectionError:
        return jsonify({"ok": False, "err": "launcher-unavailable"}), 502
    except Exception:
        return jsonify({"ok": False, "err": "launcher-error"}), 500


@api_bp.route("/api/media/close", methods=["POST"])
@require_default_rate_limit
def media_close_proxy():
    """Proxy media-close requests to the local launcher service."""
    config = current_app.config.get("CONFIG")
    base = "http://127.0.0.1:7666"
    if config and hasattr(config, "media") and config.media:
        endpoint = getattr(config.media, "launcher_endpoint", "")
        if endpoint:
            from urllib.parse import urlparse as _urlparse
            p = _urlparse(endpoint)
            base = f"{p.scheme}://{p.hostname}:{p.port}"
    token = generate_media_launcher_token(ttl_seconds=60)
    try:
        resp = _requests.post(
            f"{base}/v1/close_media",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=5,
        )
        return jsonify(resp.json()), resp.status_code
    except _requests.exceptions.ConnectionError:
        return jsonify({"ok": False, "err": "launcher-unavailable"}), 502
    except Exception:
        return jsonify({"ok": False, "err": "launcher-error"}), 500


@api_bp.route("/api/launch", methods=["POST"])
@require_default_rate_limit
def launch_app():
    """Launch an app based on config."""
    data = request.get_json(silent=True) or {}
    app_id = data.get("app_id") or request.form.get("app_id") or request.args.get("app_id")

    # Get the app configuration to determine the action
    config = current_app.config.get("CONFIG")
    if not config or (not hasattr(config, "apps") and not hasattr(config, "local_apps")):
        return jsonify({"error": "Configuration not available"}), 400

    app_config = None
    app_sources = []
    if hasattr(config, "apps"):
        app_sources.append(config.apps)
    if hasattr(config, "local_apps"):
        app_sources.append(config.local_apps)

    for app_list in app_sources:
        for app in app_list:
            if app.id == app_id:
                app_config = app
                break
        if app_config:
            break

    if not app_config:
        return jsonify({"error": f"App {app_id} not found"}), 400

    # Handle different action types
    if app_config.action == "switch_view":
        # Return the requested view template
        if app_config.target:
            if app_config.target == "week_calendar":
                view_context = _build_calendar_view_context("week")
                events = calendar.list_events(
                    view_context["range_start"].replace(tzinfo=timezone.utc),
                    view_context["range_end"].replace(tzinfo=timezone.utc),
                )
                config_dict = get_config_dict(current_app.config.get("CONFIG"))
                view_context["time_grid"] = _build_week_time_grid(
                    events, view_context["date_cells"], view_context["current_date"], datetime.now(), config_dict
                )

                return render_template(
                    "partials/calendar_week.html",
                    events=events,
                    config=config_dict,
                    timedelta=timedelta,
                    **view_context,
                )
            elif app_config.target == "media":
                return render_template("partials/media_iframe.html", current_url="https://www.youtube.com/")
            elif app_config.target == "cooking":
                return render_template("partials/cooking_mode.html")
            elif app_config.target == "sports":
                # Return the sports view template
                sports_data = sports.get_sports_data()
                config = current_app.config.get("CONFIG")
                favorite_teams = (
                    config.providers.sports.favorite_teams
                    if hasattr(config, "providers") and hasattr(config.providers, "sports")
                    else []
                )
                # Convert Pydantic model to dictionary for JSON serialization
                config_dict = get_config_dict(config)
                return render_template(
                    "partials/sports_view.html",
                    sports_data=sports_data,
                    config=config_dict,
                    favorite_teams=favorite_teams,
                )
            elif app_config.target == "status":
                if request.headers.get("HX-Request"):
                    resp = make_response("", 204)
                    resp.headers["HX-Redirect"] = "/status"
                    return resp
                return redirect("/status")
            elif app_config.target == "settings":
                if request.headers.get("HX-Request"):
                    resp = make_response("", 204)
                    resp.headers["HX-Redirect"] = "/settings"
                    return resp
                return redirect("/settings")
    elif app_config.action == "open_iframe" and app_config.url:
        # Return media iframe with the specific URL
        return render_template("partials/media_iframe.html", current_url=app_config.url)
    elif app_config.action == "open_tab":
        # For open_tab, we could return JavaScript to open a new tab
        # But for HTMX, we'll return a partial that might contain a link or iframe
        return render_template("partials/media_iframe.html", current_url=app_config.url)

    # If we get here, return a generic success response
    result = media.launch_app(app_id)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200


@api_bp.route("/api/ingredients-to-shopping", methods=["POST"])
def add_ingredients_to_shopping():
    """Add recipe ingredients to shopping list."""
    # Intentionally not using request data in this simplified implementation
    # but keeping the ability to receive POST requests

    # For this implementation, we'll use predefined ingredients for the demo recipe
    # In a full implementation, we would look up the recipe by ID
    ingredients = [
        "400g spaghetti",
        "200g pancetta or bacon",
        "4 large eggs",
        "100g Pecorino Romano cheese, grated",
        "Freshly ground black pepper",
    ]

    # Add each ingredient to the shopping list
    added_items = []
    for ingredient in ingredients:
        item = shopping.create_shopping_item(ingredient, qty=None)
        if item:
            added_items.append(item.to_dict())

    # Return alert message
    alert_html = f"""
    <div class="alert alert-success">
        <strong>Success:</strong> Added {len(added_items)} ingredients to shopping list
    </div>
    """

    return alert_html


@api_bp.route("/partials/calendar/day-events", methods=["GET"])
@require_default_rate_limit
def get_calendar_day_events():
    """Return partial for a specific day's events (for modal)."""
    date_str = request.args.get("date")
    if not date_str:
        return "Date required", 400

    try:
        target_date = datetime.fromisoformat(date_str).date()
        local_tz = ZoneInfo("America/New_York")

        # Fetch a buffer around the local day, then filter by local date to
        # match the UI grouping (handles late-night UTC spillover).
        local_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=local_tz)
        local_end = local_start + timedelta(days=1)
        range_start = (local_start - timedelta(days=1)).astimezone(timezone.utc)
        range_end = (local_end + timedelta(days=1)).astimezone(timezone.utc)

        events = calendar.list_events(range_start, range_end)
        filtered_events = []
        for event in events:
            if not event.starts_at:
                continue
            starts_at = event.starts_at
            if starts_at.tzinfo is None:
                starts_at = starts_at.replace(tzinfo=timezone.utc)
            if starts_at.astimezone(local_tz).date() == target_date:
                filtered_events.append(event)
        config = current_app.config.get("CONFIG")
        config_dict = get_config_dict(config)

        return render_template(
            "partials/calendar_day_events_modal.html",
            events=filtered_events,
            target_date=target_date,
            config=config_dict,
        )
    except Exception as e:
        current_app.logger.error(f"Error fetching day events: {e}")
        return str(e), 500


@api_bp.route("/partials/calendar/week", methods=["GET"])
@require_default_rate_limit
def get_calendar_week():
    """Return week grid partial."""
    view = request.args.get("view", "week")
    offset = _safe_int(request.args.get("offset"), 0)
    month_offset = _safe_int(request.args.get("month_offset"), 0)

    view_context = _build_calendar_view_context(view, offset_days=offset, month_offset=month_offset)

    events = calendar.list_events(
        view_context["range_start"].replace(tzinfo=timezone.utc), view_context["range_end"].replace(tzinfo=timezone.utc)
    )
    config = current_app.config.get("CONFIG")

    # Convert Pydantic model to dictionary for JSON serialization
    config_dict = get_config_dict(config)

    if view_context["view_mode"] in ("week", "workweek"):
        view_context["time_grid"] = _build_week_time_grid(
            events, view_context["date_cells"], view_context["current_date"], datetime.now(), config_dict
        )

    return render_template(
        "partials/calendar_week.html",
        events=events,
        config=config_dict,
        timedelta=timedelta,
        **view_context,
    )


@api_bp.route("/partials/calendar/upnext", methods=["GET"])
@require_default_rate_limit
def get_calendar_upnext():
    """Return up next list partial."""
    upcoming_events = calendar.get_upcoming_events(5)
    config = current_app.config.get("CONFIG")
    # Convert Pydantic model to dictionary for JSON serialization
    config_dict = get_config_dict(config)
    now = datetime.now()
    return render_template(
        "partials/calendar_upnext.html",
        events=upcoming_events,
        config=config_dict,
        now=now,
        current_date=now.date(),
    )


@api_bp.route("/partials/notes", methods=["GET"])
@require_default_rate_limit
def get_notes():
    """Return notes panel partial."""
    all_notes = notes.list_notes()
    config = current_app.config.get("CONFIG")
    # Convert Pydantic model to dictionary for JSON serialization
    config_dict = get_config_dict(config)
    return render_template("partials/notes_panel.html", notes=all_notes, config=config_dict)


@api_bp.route("/partials/shopping", methods=["GET"])
@require_default_rate_limit
def get_shopping():
    """Return shopping panel partial."""
    all_items = shopping.list_shopping_items()
    active_count = sum(1 for item in all_items if not item.done)
    config = current_app.config.get("CONFIG")
    # Convert Pydantic model to dictionary for JSON serialization
    config_dict = get_config_dict(config)
    template_name = "partials/shopping_tile.html" if request.args.get("context") == "tile" else "partials/shopping_panel.html"
    return render_template(
        template_name,
        items=all_items,
        active_count=active_count,
        config=config_dict,
    )


@api_bp.route("/partials/weather", methods=["GET"])
@require_default_rate_limit
def get_weather():
    """Return weather panel partial."""
    weather_data = weather.get_weather_data()
    config = current_app.config.get("CONFIG")
    # Convert Pydantic model to dictionary for JSON serialization
    config_dict = get_config_dict(config)
    return render_template("partials/weather_panel.html", weather=weather_data, config=config_dict)


@api_bp.route("/partials/weather-modal", methods=["GET"])
@require_default_rate_limit
def get_weather_modal():
    """Return weather forecast modal partial with hourly/daily tabs."""
    view = request.args.get("view", "hourly")
    weather_data = weather.get_weather_data()
    config = current_app.config.get("CONFIG")
    config_dict = get_config_dict(config)
    return render_template(
        "partials/weather_modal.html",
        weather=weather_data,
        active_view=view,
        config=config_dict,
    )


@api_bp.route("/partials/media", methods=["GET"])
@require_default_rate_limit
def get_media():
    """Return media iframe partial."""
    config = current_app.config.get("CONFIG")
    # Get URL from query parameter, default to YouTube
    url = request.args.get("url", "https://www.youtube.com/")
    # Convert Pydantic model to dictionary for JSON serialization
    config_dict = get_config_dict(config)
    return render_template("partials/media_iframe.html", config=config_dict, current_url=url)


@api_bp.route("/partials/sports", methods=["GET"])
@require_default_rate_limit
def get_sports():
    """Return sports ticker partial."""
    sports_data = sports.get_sports_data()
    config = current_app.config.get("CONFIG")
    # Convert Pydantic model to dictionary for JSON serialization
    config_dict = get_config_dict(config)
    return render_template("partials/sports_ticker.html", sports_data=sports_data, config=config_dict)


@api_bp.route("/api/sidebar/counts", methods=["GET"])
@require_default_rate_limit
def get_sidebar_counts():
    """Return JSON with counts for sidebar badges."""
    return jsonify(
        {
            "notes": notes.count_notes(),
            "shopping": shopping.count_active_shopping_items(),
            "timers": timers.count_active_timers(),
        }
    )


@api_bp.route("/api/status/weather", methods=["GET"])
def get_weather_status():
    """Return weather status with last updated time."""
    weather_data = weather.get_weather_data()
    return _format_weather_status_text(weather_data, include_prefix=False)


@api_bp.route("/api/status/weather-toast", methods=["GET"])
def get_weather_status_toast():
    """Display weather status as a toast notification."""
    weather_data = weather.get_weather_data()
    status_text = _format_weather_status_text(weather_data, include_prefix=True)

    # Use JavaScript to show the toast notification
    script = f"""
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            if (window.toast) {{
                window.toast.info('{status_text}');
            }}
        }});
    </script>
    """
    return script


@api_bp.route("/api/status/calendar-toast", methods=["GET"])
def get_calendar_status_toast():
    """Display calendar status as a toast notification."""
    # Use the calendar service function to get status
    status_info = calendar.get_calendar_status()
    message = _format_calendar_status_text(status_info)

    # Use JavaScript to show the toast notification
    script = f"""
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            if (window.toast) {{
                window.toast.info('{message}');
            }}
        }});
    </script>
    """
    return script


@api_bp.route("/api/status/system", methods=["GET"])
def get_system_status():
    """Display system status as a toast notification."""
    # This endpoint is called less frequently (every 5 minutes) to avoid spam
    system_info = f"Kitchen Hub v{__version__} running normally on {platform.system()}"

    # Use JavaScript to show the toast notification
    script = f"""
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            if (window.toast) {{
                window.toast.success('{system_info}');
            }}
        }});
    </script>
    """
    return script


@api_bp.route("/api/status/summary", methods=["GET"])
@require_default_rate_limit
def get_status_summary():
    """Return consolidated status for badges and toasts in a single call."""
    weather_status = _format_weather_status_text(weather.get_weather_data(), include_prefix=True)
    calendar_status = _format_calendar_status_text(calendar.get_calendar_status())
    system_info = f"Kitchen Hub v{__version__} running normally on {platform.system()}"

    return jsonify(
        {
            "sidebar_counts": {
                "notes": notes.count_notes(),
                "shopping": shopping.count_active_shopping_items(),
                "timers": timers.count_active_timers(),
            },
            "messages": {
                "system": system_info,
                "weather": weather_status,
                "calendar": calendar_status,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@api_bp.route("/api/timers", methods=["GET"])
@require_default_rate_limit
def get_timers():
    """Get all active timers."""
    active_timers = timers.list_active_timers()
    return jsonify([timer.to_dict() for timer in active_timers])


@api_bp.route("/api/timers", methods=["POST"])
@require_default_rate_limit
def create_timer():
    """Create a new timer."""
    data = request.get_json(silent=True) or {}
    if not data and request.form:
        data = request.form.to_dict()

    label = (data.get("label") or "New Timer").strip() or "New Timer"
    minutes_raw = data.get("minutes")
    seconds_raw = data.get("seconds")

    try:
        minutes_val = int(minutes_raw) if minutes_raw not in (None, "", "None") else None
        seconds_val = int(seconds_raw) if seconds_raw not in (None, "", "None") else None
    except (TypeError, ValueError):
        return jsonify({"error": "Timer duration must be numeric"}), 400

    if minutes_val is not None or seconds_val is not None:
        total_seconds = (minutes_val or 0) * 60 + (seconds_val or 0)
    else:
        total_seconds = 60  # fallback default

    if total_seconds <= 0:
        return jsonify({"error": "Timer duration must be greater than zero"}), 400

    try:
        new_timer = timers.create_timer(label, total_seconds)
        if request.headers.get("HX-Request"):
            response = make_response(jsonify(new_timer.to_dict()), 201)
            response.headers["HX-Trigger"] = "refreshSidebarCounts"
            return response
        return jsonify(new_timer.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route("/api/calendar/events/<event_id>", methods=["DELETE"])
@require_admin_rate_limit
def delete_calendar_event(event_id):
    """Delete a calendar event from a writable source."""
    data = request.get_json(silent=True) or {}
    source = (data.get("source") or request.args.get("source") or "").strip()
    calendar_id = data.get("calendar_id") or request.args.get("calendar_id")

    if not source:
        return jsonify({"error": "Event source is required"}), 400

    if source.lower() == "ics":
        return jsonify({"error": "ICS events are read-only"}), 400

    success = calendar.delete_event(event_id, source, calendar_id)
    if not success:
        return jsonify({"error": "Event not found or could not be deleted"}), 404

    return jsonify({"status": "deleted"}), 200


@api_bp.route("/api/timers/<int:id>", methods=["GET"])
@require_default_rate_limit
def get_timer(id):
    """Get a specific timer."""
    timer = timers.get_timer(id)
    if not timer:
        return jsonify({"error": "Timer not found"}), 404
    return jsonify(timer.to_dict())


@api_bp.route("/api/timers/<int:id>", methods=["DELETE"])
@require_admin_rate_limit
def delete_timer(id):
    """Delete a timer."""
    success = timers.delete_timer(id)
    if not success:
        return jsonify({"error": "Timer not found"}), 404

    if request.headers.get("HX-Request"):
        response = make_response(jsonify({"status": "deleted"}), 200)
        response.headers["HX-Trigger"] = "refreshSidebarCounts"
        return response

    return jsonify({"status": "deleted"}), 200


@api_bp.route("/api/timers/<int:id>", methods=["PUT"])
@require_admin_rate_limit
def update_timer(id):
    """Update a timer."""
    data = request.get_json(silent=True) or {}
    label = data.get("label")
    seconds = data.get("seconds")
    active = data.get("active")

    updated_timer = timers.update_timer(id, label, seconds, active)
    if not updated_timer:
        return jsonify({"error": "Timer not found"}), 404

    if request.headers.get("HX-Request"):
        response = make_response(jsonify(updated_timer.to_dict()), 200)
        response.headers["HX-Trigger"] = "refreshSidebarCounts"
        return response

    return jsonify(updated_timer.to_dict())


@api_bp.route("/partials/timers", methods=["GET"])
@require_default_rate_limit
def get_timers_partial():
    """Return timers panel partial."""
    active_timers = timers.list_active_timers()
    config = current_app.config.get("CONFIG")
    # Convert Pydantic model to dictionary for JSON serialization
    config_dict = get_config_dict(config)
    return render_template("partials/timers_panel.html", timers=active_timers, config=config_dict)


@api_bp.route("/api/status/calendar", methods=["GET"])
def get_calendar_status():
    """Return calendar status with last updated time."""
    # Use the calendar service function to get status
    status_info = calendar.get_calendar_status()

    # Format a user-friendly message
    if "refresh_interval" in status_info:
        return f"{status_info['status']}, refreshing every {status_info['refresh_interval']}"
    else:
        return status_info.get("status", "Calendar status unknown")


@api_bp.route("/partials/alerts", methods=["GET"])
def get_alerts():
    """Return error/status banner partial."""
    return render_template("partials/alerts_banner.html", status={})


@api_bp.route("/api/voice/recognize", methods=["POST"])
@require_default_rate_limit
def process_voice_command():
    """Process a voice command received from the frontend."""
    config = current_app.config.get("CONFIG", {})
    if not getattr(getattr(config, "features", None), "voice", False):
        return jsonify({"error": "Voice commands are not enabled"}), 400

    data = request.get_json(silent=True) or {}
    command = data.get("command", "").strip()

    if not command:
        return jsonify({"error": "No command provided"}), 400

    try:
        # Get the apps config to pass to the voice service
        apps_config = getattr(config, "apps", [])
        result = voice.process_voice_command(command, apps_config)
        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Error processing voice command: {e}")
        return jsonify({"error": "Failed to process voice command"}), 500


@api_bp.route("/api/voice/commands", methods=["GET"])
def get_voice_commands():
    """Get a list of available voice commands."""
    config = current_app.config.get("CONFIG")
    enabled = bool(config and getattr(getattr(config, "features", None), "voice", False))
    if not enabled:
        return jsonify({"commands": [], "enabled": False}), 200

    commands = voice.get_available_commands()
    return jsonify({"commands": commands, "enabled": True}), 200


@api_bp.route("/api/voice/status", methods=["GET"])
def get_voice_status():
    """Get the status of the voice command feature."""
    config = current_app.config.get("CONFIG")
    is_enabled = config.features.voice if config and hasattr(config, "features") else False

    return jsonify({"enabled": is_enabled, "status": "active" if is_enabled else "inactive"})


@api_bp.route("/api/config", methods=["GET"])
def get_app_config():
    """Get application configuration (excluding sensitive data)."""
    config = current_app.config.get("CONFIG")

    if not config:
        return jsonify({"error": "Configuration not available"}), 400

    # Return only non-sensitive configuration
    public_config = {
        "features": {
            "voice": config.features.voice,
            "voice_wake_word": config.features.voice_wake_word,
            "kiosk": config.features.kiosk,
            "auth": config.features.auth,
        },
        "ui": {"theme": config.ui.theme, "density": config.ui.density},
        "layout": config.layout,
    }

    return jsonify(public_config)


@api_bp.route("/api/calendar/google", methods=["POST"])
def create_google_calendar_event():
    """Create a new event in Google Calendar."""
    config = current_app.config.get("CONFIG")
    if not config or not hasattr(config, "providers") or not hasattr(config.providers, "calendar"):
        return jsonify({"error": "Calendar configuration not available"}), 400

    calendar_config = config.providers.calendar
    if calendar_config.kind != "google" or not calendar_config.google:
        return jsonify({"error": "Google Calendar not configured"}), 400

    data = request.get_json(silent=True) or {}
    title = data.get("title", "")
    starts_at_str = data.get("starts_at", "")
    ends_at_str = data.get("ends_at", "")
    location = data.get("location")

    try:
        starts_at = datetime.fromisoformat(starts_at_str.replace("Z", "+00:00"))
        ends_at = datetime.fromisoformat(ends_at_str.replace("Z", "+00:00"))

        event = calendar.add_google_calendar_event(title, starts_at, ends_at, location)
        if event:
            return jsonify(event.to_dict()), 201
        else:
            return jsonify({"error": "Failed to create event in Google Calendar"}), 500
    except ValueError as e:
        return jsonify({"error": f"Invalid date format: {e}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/oauth/google", methods=["GET"])
@require_ip_whitelist
def google_calendar_auth():
    """Initiate Google Calendar OAuth flow."""
    config = current_app.config.get("CONFIG")
    if not config or not hasattr(config, "providers") or not hasattr(config.providers, "calendar"):
        return jsonify({"error": "Calendar configuration not available"}), 400

    calendar_config = config.providers.calendar
    if calendar_config.kind != "google" or not calendar_config.google:
        return jsonify({"error": "Google Calendar not configured"}), 400

    google_config = calendar_config.google

    # Create client config
    client_config = {
        "web": {
            "client_id": google_config.get("client_id", ""),
            "client_secret": google_config.get("client_secret", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",  # nosec B105
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        }
    }

    try:
        # Create flow instance
        flow = Flow.from_client_config(
            client_config, scopes=["https://www.googleapis.com/auth/calendar"], redirect_uri="http://localhost"
        )

        # Generate authorization URL
        auth_url, _ = flow.authorization_url(prompt="consent")

        return jsonify({"auth_url": auth_url})
    except Exception as e:
        return jsonify({"error": f"Failed to initiate Google OAuth: {str(e)}"}), 500


@api_bp.route("/api/oauth/google/callback", methods=["GET"])
@require_ip_whitelist
def google_calendar_auth_callback():
    """Handle Google Calendar OAuth callback."""
    config = current_app.config.get("CONFIG")
    if not config or not hasattr(config, "providers") or not hasattr(config.providers, "calendar"):
        return jsonify({"error": "Calendar configuration not available"}), 400

    calendar_config = config.providers.calendar
    if calendar_config.kind != "google" or not calendar_config.google:
        return jsonify({"error": "Google Calendar not configured"}), 400

    google_config = calendar_config.google

    # Create client config
    client_config = {
        "web": {
            "client_id": google_config.get("client_id", ""),
            "client_secret": google_config.get("client_secret", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",  # nosec B105
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        }
    }

    try:
        # Create flow instance
        flow = Flow.from_client_config(
            client_config, scopes=["https://www.googleapis.com/auth/calendar"], redirect_uri="http://localhost"
        )

        # Exchange authorization code for access token
        flow.fetch_token(authorization_response=request.url)

        # Save credentials to instance directory
        credentials = flow.credentials
        token_path = os.path.join(current_app.instance_path, "token.json")
        with open(token_path, "w") as token:
            token.write(credentials.to_json())

        return jsonify({"status": "Authentication successful"})
    except Exception as e:
        return jsonify({"error": f"Failed to complete Google OAuth: {str(e)}"}), 500


@api_bp.route("/api/ha/entities", methods=["GET"])
@require_ip_whitelist
def get_ha_entities():
    """Get all Home Assistant entities."""
    config = current_app.config.get("CONFIG")
    if not config or not hasattr(config, "providers") or not hasattr(config.providers, "homeassistant"):
        return jsonify({"error": "Home Assistant configuration not available"}), 400

    ha_config = config.providers.homeassistant

    adapter = initialize_ha_adapter(ha_config)
    if not adapter:
        return jsonify({"error": "Failed to initialize Home Assistant adapter"}), 500

    domain = request.args.get("domain")  # Optional domain filter
    entities = adapter.get_entities(domain)
    return jsonify(entities)


@api_bp.route("/api/ha/entities/<entity_id>", methods=["GET"])
@require_ip_whitelist
def get_ha_entity(entity_id):
    """Get a specific Home Assistant entity state."""
    config = current_app.config.get("CONFIG")
    if not config or not hasattr(config, "providers") or not hasattr(config.providers, "homeassistant"):
        return jsonify({"error": "Home Assistant configuration not available"}), 400

    ha_config = config.providers.homeassistant

    adapter = initialize_ha_adapter(ha_config)
    if not adapter:
        return jsonify({"error": "Failed to initialize Home Assistant adapter"}), 500

    entity_state = adapter.get_entity_state(entity_id)
    if entity_state:
        return jsonify(entity_state)
    else:
        return jsonify({"error": f"Entity {entity_id} not found"}), 404


@api_bp.route("/api/ha/services/<domain>/<service>", methods=["POST"])
@require_ip_whitelist
@require_admin_rate_limit
def call_ha_service(domain, service):
    """Call a Home Assistant service."""
    config = current_app.config.get("CONFIG")
    if not config or not hasattr(config, "providers") or not hasattr(config.providers, "homeassistant"):
        return jsonify({"error": "Home Assistant configuration not available"}), 400

    ha_config = config.providers.homeassistant

    adapter = initialize_ha_adapter(ha_config)
    if not adapter:
        return jsonify({"error": "Failed to initialize Home Assistant adapter"}), 500

    data = request.get_json(silent=True) or {}
    service_data = data or {}

    success = adapter.call_service(domain, service, service_data)
    if success:
        return jsonify({"status": "Service call successful"})
    else:
        return jsonify({"error": f"Failed to call service {domain}.{service}"}), 500
