"""E2E tests for the Family Hub dashboard."""

import pytest
from playwright.sync_api import Page, expect

from .pages.dashboard_page import DashboardPage

# ---------------------------------------------------------------------------
# Dashboard structure
# ---------------------------------------------------------------------------


def test_page_title(page: Page, live_server_url: str):
    """Page has correct title."""
    page.goto(live_server_url)
    expect(page).to_have_title("Kitchen Hub")


def test_main_structural_elements_visible(page: Page, live_server_url: str):
    """Main content area, sidebar, and app bar are all present."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.goto()

    expect(dashboard.main_content).to_be_visible()
    expect(dashboard.sidebar).to_be_visible()
    expect(dashboard.app_bar).to_be_visible()


def test_alerts_container_present(page: Page, live_server_url: str):
    """Alerts container is in the DOM (used for live notifications)."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.goto()

    expect(dashboard.alerts_container).to_be_attached()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def test_sidebar_action_buttons_visible(page: Page, live_server_url: str):
    """Notes, Shopping, Timers, and Kitchen Reference buttons are visible."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.goto()

    expect(dashboard.notes_button).to_be_visible()
    expect(dashboard.shopping_button).to_be_visible()
    expect(dashboard.timers_button).to_be_visible()
    expect(dashboard.kitchen_reference_button).to_be_visible()


def test_sidebar_clock_elements_present(page: Page, live_server_url: str):
    """Clock and date elements exist in the sidebar."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.goto()

    expect(dashboard.system_time).to_be_attached()
    expect(dashboard.system_date).to_be_attached()


def test_weather_panel_in_sidebar(page: Page, live_server_url: str):
    """Weather panel is rendered in the sidebar (per config)."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.goto()

    expect(dashboard.weather_panel).to_be_attached()


# ---------------------------------------------------------------------------
# Main content / default view
# ---------------------------------------------------------------------------


def test_calendar_container_on_default_view(page: Page, live_server_url: str):
    """Calendar container is rendered on the default (week_calendar) view."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.goto()

    expect(dashboard.calendar_container).to_be_attached()


def test_home_dashboard_shows_miniplayer_playlist_list(page: Page, live_server_url: str):
    """The sidebar miniplayer exposes the expanded recent-playlist list shell."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.goto()

    expect(dashboard.miniplayer).to_be_attached()
    expect(dashboard.playlist_list).to_be_attached()


def test_home_dashboard_shows_live_sports_ticker_context(page: Page, live_server_url: str):
    """The home dashboard ticker shows live game phase context from the mock feed."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.goto()

    expect(dashboard.sports_ticker).to_be_attached()
    expect(dashboard.sports_ticker).to_contain_text("Q3")


# ---------------------------------------------------------------------------
# App bar navigation
# ---------------------------------------------------------------------------


def test_app_bar_has_buttons(page: Page, live_server_url: str):
    """App bar contains at least one navigation button."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.goto()

    expect(dashboard.app_bar_buttons.first).to_be_visible()


def test_app_bar_calendar_button_present(page: Page, live_server_url: str):
    """Calendar app button is present (matches test config)."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.goto()

    expect(dashboard.app_bar_button("calendar")).to_be_visible()


def test_app_bar_youtube_button_present(page: Page, live_server_url: str):
    """YouTube app button is present (matches test config)."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.goto()

    expect(dashboard.app_bar_button("youtube")).to_be_visible()


# ---------------------------------------------------------------------------
# View routing
# ---------------------------------------------------------------------------


def test_sports_view_renders(page: Page, live_server_url: str):
    """/view/sports renders the sports dashboard partial."""
    page.goto(f"{live_server_url}/view/sports")
    page.wait_for_load_state("domcontentloaded")

    # The sports route renders partials/sports_view.html directly (not base.html)
    expect(page.locator("#sports-view")).to_be_attached()


def test_media_view_renders(page: Page, live_server_url: str):
    """/view/media renders the media container."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.goto_view("media")

    expect(dashboard.media_container).to_be_attached()


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


def test_health_endpoint_ok(page: Page, live_server_url: str):
    """/health returns HTTP 200."""
    response = page.request.get(f"{live_server_url}/health")
    assert response.status == 200


def test_health_endpoint_json(page: Page, live_server_url: str):
    """/health response body is valid JSON with a status field."""
    response = page.request.get(f"{live_server_url}/health")
    body = response.json()
    assert "status" in body
