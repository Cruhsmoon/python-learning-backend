"""
SearchResultsPage
=================
Page Object for https://www.greenbook.org/keyword-search-results?q=<query>

Key DOM facts (verified against live site):
  - Company result cards : <a href="/company/<Slug>"><h4>Name</h4></a>
  - Result count text    : element containing text matching r"\\d+ results?"
  - Content-type tabs    : may be rendered as <button> or role="tab" elements
                           with labels All / Specialties / Firms & Products /
                           Case Studies / Articles
  - Pagination control   : "View all" <button>, or Next/Load More equivalents
  - No traditional checkbox filter panel (filters are link/tab-based)
"""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

from .base_page import BasePage

_SEARCH_PATH = "/keyword-search-results"

# Ordered list of result-type tab labels to probe.
CONTENT_TABS = ["Specialties", "Firms & Products", "Articles", "Case Studies", "All"]


class SearchResultsPage(BasePage):
    """Page Object for Greenbook keyword search results."""

    def navigate(self, query: str) -> None:
        """Load the search results page for *query*."""
        self.navigate_to(f"{_SEARCH_PATH}?q={query}")

    # ── Locators ─────────────────────────────────────────────────────────────

    @property
    def company_cards(self) -> Locator:
        """All visible links to /company/ profile pages."""
        return self.page.locator("a[href*='/company/']")

    @property
    def result_count_element(self) -> Locator:
        """
        Element that displays a numeric result count (e.g., '26 results').
        Uses a regex text match so it works regardless of surrounding text.
        """
        return self.page.locator("text=/\\d+ results?/i").first

    @property
    def view_all_button(self) -> Locator:
        """'View all' button that expands the full result set."""
        return self.page.get_by_role(
            "button", name=re.compile(r"view\s+all", re.IGNORECASE)
        )

    @property
    def next_page_control(self) -> Locator:
        """
        Returns the first available pagination / expansion control found on
        the page.  Checks Next, Load More, and View All in that order.
        """
        candidates = [
            self.page.get_by_role(
                "button", name=re.compile(r"^next", re.IGNORECASE)
            ),
            self.page.get_by_role(
                "link", name=re.compile(r"^next", re.IGNORECASE)
            ),
            self.page.locator("[aria-label='Next page'], [aria-label*='Next' i]"),
            self.page.get_by_role(
                "button", name=re.compile(r"load\s+more", re.IGNORECASE)
            ),
            self.view_all_button,
        ]
        for candidate in candidates:
            if candidate.count() > 0:
                return candidate.first
        # Return view_all_button as the final fallback (caller checks .count()).
        return self.view_all_button.first

    def content_tab(self, name: str) -> Locator:
        """
        Locate a content-type filter tab by its visible label.
        Handles role="tab", role="button", or plain text nodes.
        """
        return (
            self.page.get_by_role("tab", name=name)
            .or_(self.page.get_by_role("button", name=name))
            .or_(self.page.locator(f"text='{name}'").first)
        )

    # ── Queries ──────────────────────────────────────────────────────────────

    def result_count(self) -> int:
        """Number of company cards currently visible on the page."""
        return self.company_cards.count()

    def has_results(self) -> bool:
        return self.result_count() > 0

    def first_company_href(self) -> str:
        href = self.company_cards.first.get_attribute("href")
        return href or ""

    def has_pagination_control(self) -> bool:
        """Return True if any next-page / load-more / view-all control exists."""
        probes = [
            self.page.get_by_role(
                "button",
                name=re.compile(r"next|load\s+more|view\s+all", re.IGNORECASE),
            ),
            self.page.get_by_role(
                "link", name=re.compile(r"^next", re.IGNORECASE)
            ),
            self.page.locator("[aria-label*='Next' i]"),
        ]
        return any(p.count() > 0 for p in probes)

    def first_available_tab(self) -> str | None:
        """Return the label of the first content-type tab found, or None."""
        for name in CONTENT_TABS:
            if self.content_tab(name).count() > 0:
                return name
        return None

    # ── Actions ──────────────────────────────────────────────────────────────

    def click_content_tab(self, name: str) -> None:
        """Click a content-type filter tab and wait for the page to settle."""
        self.content_tab(name).click()
        self.page.wait_for_load_state("networkidle")

    def click_next_or_view_all(self) -> None:
        """
        Click the first available pagination / view-all control.

        Raises:
            LookupError: if no control is found.
        """
        if not self.has_pagination_control():
            raise LookupError(
                "No 'Next page', 'Load more', or 'View all' control found."
            )
        self.next_page_control.click()
        self.page.wait_for_load_state("networkidle")
