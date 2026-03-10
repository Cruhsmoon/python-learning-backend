"""HomePage — Page Object for https://www.greenbook.org/."""

from __future__ import annotations

from playwright.sync_api import Locator, Page

from .base_page import BasePage
from .navigation_bar import NavigationBar


class HomePage(BasePage):
    """
    Page Object for the Greenbook homepage.

    Composes :class:`NavigationBar` for site-wide navigation so tests can
    do ``home.nav_bar.go_to_insights()`` without knowing selector details.
    """

    def __init__(self, page: Page, base_url: str) -> None:
        super().__init__(page, base_url)

        # ── Composed page objects ────────────────────────────────────────────
        self.nav_bar: NavigationBar = NavigationBar(page, base_url)

        # ── Locators ─────────────────────────────────────────────────────────
        # Primary navigation landmark.
        self.nav_landmark: Locator = page.locator("nav").first

        # Hero search input.
        # Live site: <input type="search" placeholder="Find suppliers, …">
        self.search_input: Locator = page.locator("input[type='search']")

    # ── Actions ──────────────────────────────────────────────────────────────

    def navigate(self) -> None:
        """Load the homepage and wait until the network is idle."""
        self.navigate_to("/")

    def search(self, query: str) -> None:
        """
        Fill the search box and press Enter.

        Waits for the client-side router (Next.js) to commit the navigation
        to ``/keyword-search-results`` before returning.
        """
        self.search_input.wait_for(state="visible", timeout=10_000)
        self.search_input.fill(query)
        self.search_input.press("Enter")
        self.page.wait_for_url("**/keyword-search-results**", timeout=10_000)

    # ── Queries ──────────────────────────────────────────────────────────────

    def is_nav_visible(self) -> bool:
        """Return True if the main <nav> landmark is visible."""
        return self.nav_landmark.is_visible()

    def has_link_to(self, href: str) -> bool:
        """Return True if at least one <a href="{href}"> exists on the page."""
        return self.page.locator(f"a[href='{href}']").count() > 0
