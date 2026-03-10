"""ResultsPage — Page Object for the search results listing area."""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page


class ResultsPage:
    """
    Encapsulates every locator and action related to search result cards.

    This object does NOT inherit from BasePage because it represents a
    sub-component of the search results page rather than a top-level page.
    It is composed inside :class:`SearchPage`.

    DOM facts (verified against live site):
    - Company cards  : ``<a href="/company/<slug>"><h4>Name</h4></a>``
    - Result count   : element containing text matching ``\\d+ results``
    - Expand control : "View all" ``<button>``
    """

    def __init__(self, page: Page) -> None:
        self._page = page

        # ── Locators stored at construction time ─────────────────────────────
        self.company_cards: Locator = page.locator("a[href*='/company/']")

        self.result_count_label: Locator = (
            page.locator("text=/\\d+ results?/i").first
        )

        self.view_all_button: Locator = page.get_by_role(
            "button", name=re.compile(r"view\s+all", re.IGNORECASE)
        ).first

        self.load_more_button: Locator = page.get_by_role(
            "button", name=re.compile(r"load\s+more", re.IGNORECASE)
        )

    # ── Queries ──────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Number of company cards currently visible."""
        return self.company_cards.count()

    def has_results(self) -> bool:
        return self.count() > 0

    def first_card_href(self) -> str:
        return self.company_cards.first.get_attribute("href") or ""

    def result_count_text(self) -> str:
        """Inner text of the result-count label, e.g. '26 results'."""
        return (
            self.result_count_label.inner_text()
            if self.result_count_label.count() > 0
            else ""
        )

    def has_pagination_control(self) -> bool:
        """Return True if any expand/load/next control is present."""
        return (
            self.view_all_button.count() > 0
            or self.load_more_button.count() > 0
            or self._page.get_by_role(
                "link", name=re.compile(r"next", re.IGNORECASE)
            ).count() > 0
        )

    # ── Waits ────────────────────────────────────────────────────────────────

    def wait_for_cards(self, timeout: int = 15_000) -> None:
        """Block until at least one company card is present in the DOM."""
        self._page.wait_for_selector("a[href*='/company/']", timeout=timeout)

    # ── Actions ──────────────────────────────────────────────────────────────

    def click_view_all(self) -> None:
        """Click the 'View all' button and wait for the page to settle."""
        if self.view_all_button.count() > 0:
            self.view_all_button.click()
        elif self.load_more_button.count() > 0:
            self.load_more_button.click()
        else:
            raise LookupError("No pagination control found on results page.")
        self._page.wait_for_load_state("networkidle")
