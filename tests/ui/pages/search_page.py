"""SearchPage — Page Object for /keyword-search-results."""

from __future__ import annotations

from playwright.sync_api import Page

from .base_page import BasePage
from .filters_panel import FiltersPanel
from .results_page import ResultsPage


class SearchPage(BasePage):
    """
    Page Object for the Greenbook keyword-search results page.

    URL pattern: ``/keyword-search-results?q=<query>``

    Composes :class:`FiltersPanel` and :class:`ResultsPage` so callers can
    use ``search_page.filters.click_tab("Articles")`` and
    ``search_page.results.count()`` without knowing any selectors.
    """

    _PATH: str = "/keyword-search-results"

    def __init__(self, page: Page, base_url: str) -> None:
        super().__init__(page, base_url)

        # ── Composed sub-components ──────────────────────────────────────────
        self.filters: FiltersPanel = FiltersPanel(page)
        self.results: ResultsPage = ResultsPage(page)

    # ── Navigation ───────────────────────────────────────────────────────────

    def navigate(self, query: str) -> None:
        """
        Navigate directly to the search results page for *query* and wait
        until the network is idle.
        """
        self.navigate_to(f"{self._PATH}?q={query}")

    # ── Queries ──────────────────────────────────────────────────────────────

    def is_on_search_page(self) -> bool:
        """Return True if the current URL is the search results page."""
        return self._PATH in self.current_url or "q=" in self.current_url
