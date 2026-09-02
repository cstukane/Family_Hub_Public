"""Page Object Model for the Family Hub dashboard."""

from playwright.sync_api import Page


class DashboardPage:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def goto(self):
        self.page.goto(self.base_url)
        self.page.wait_for_load_state("domcontentloaded")

    def goto_view(self, view_name: str):
        self.page.goto(f"{self.base_url}/view/{view_name}")
        self.page.wait_for_load_state("domcontentloaded")

    # --- Structural elements ---

    @property
    def main_content(self):
        return self.page.locator("#main-content")

    @property
    def sidebar(self):
        return self.page.locator(".sidebar")

    @property
    def app_bar(self):
        return self.page.locator(".app-bar")

    @property
    def alerts_container(self):
        return self.page.locator("#alerts-container")

    # --- Sidebar widgets ---

    @property
    def system_time(self):
        return self.page.locator("#system-time")

    @property
    def system_date(self):
        return self.page.locator("#system-date")

    @property
    def notes_button(self):
        return self.page.locator("#notes-icon-btn")

    @property
    def shopping_button(self):
        return self.page.locator("#shopping-icon-btn")

    @property
    def timers_button(self):
        return self.page.locator("#timers-icon-btn")

    @property
    def kitchen_reference_button(self):
        return self.page.locator("#kitchen-reference-btn")

    @property
    def weather_panel(self):
        return self.page.locator("#weather-panel")

    @property
    def miniplayer(self):
        return self.page.locator("#miniplayer")

    @property
    def playlist_list(self):
        return self.page.locator("#spotify-playlist-list")

    @property
    def sports_ticker(self):
        return self.page.locator("#sports-horizontal-ticker")

    # --- Main view containers ---

    @property
    def calendar_container(self):
        return self.page.locator("#calendar-container")

    @property
    def sports_container(self):
        # /view/sports renders partials/sports_view.html with id="sports-view"
        return self.page.locator("#sports-view")

    @property
    def media_container(self):
        return self.page.locator("#media-container")

    # --- App bar ---

    @property
    def app_bar_buttons(self):
        return self.page.locator(".app-bar-btn")

    def app_bar_button(self, app_id: str):
        return self.page.locator(f'.app-bar-btn[data-app-id="{app_id}"]')
