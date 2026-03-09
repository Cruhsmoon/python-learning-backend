"""
HomePage
========
Page Object for https://www.greenbook.org/

Greenbook is a Next.js single-page application.  Navigation links are plain
<a> tags; the search bar submits to /keyword-search-results?q=<query>.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page

from .base_page import BasePage


class HomePage(BasePage):
    """Page Object for the Greenbook homepage."""

    def navigate(self) -> None:
        """Load the homepage and wait until idle."""
        self.navigate_to("/")

    # ── Locators ─────────────────────────────────────────────────────────────

    @property
    def nav(self) -> Locator:
        """Top-level navigation container (<nav> or [role='navigation'])."""
        return self.page.locator("nav, [role='navigation']").first

    @property
    def search_input(self) -> Locator:
        """
        Search text field.  Tries several stable selectors in priority order
        so that minor DOM changes do not break the locator immediately.
        """
        for candidate in (
            self.page.get_by_role("searchbox"),
            self.page.locator("input[type='search']"),
            self.page.locator("input[name='q']"),
            self.page.locator("input[placeholder*='Search' i]"),
            self.page.locator("input[placeholder*='Find' i]"),
        ):
            if candidate.count() > 0:
                return candidate.first
        # Absolute fallback: any visible text input in the header area.
        return self.page.locator("header input[type='text'], header input").first

    # ── Actions ──────────────────────────────────────────────────────────────

    def search(self, query: str) -> None:
        """Fill the search input and press Enter to navigate to results."""
        inp = self.search_input
        inp.wait_for(state="visible", timeout=10_000)
        inp.fill(query)
        inp.press("Enter")
        self.page.wait_for_load_state("networkidle")

    def click_nav_link(self, href: str) -> None:
        """
        Click a navigation anchor identified by its exact href attribute.
        Waits for network to be idle after navigation.
        """
        self.page.locator(
            f"nav a[href='{href}'], header a[href='{href}']"
        ).first.click()
        self.page.wait_for_load_state("networkidle")

    def nav_link_texts(self) -> list[str]:
        """Return the inner text of every visible navigation link."""
        return self.page.locator("nav a").all_inner_texts()
