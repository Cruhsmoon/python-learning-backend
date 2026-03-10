"""FiltersPanel — Page Object for content-type filter tabs on the search page."""

from __future__ import annotations

from playwright.sync_api import Locator, Page


class FiltersPanel:
    """
    Encapsulates the content-type filter tabs on Greenbook's search results page.

    Greenbook does not expose a traditional checkbox filter sidebar.  Instead
    it uses result-type tabs (Specialties, Firms & Products, Articles,
    Case Studies, All) to narrow the visible content set.

    Each tab locator is stored at construction time so tests can reference
    them without knowledge of underlying selectors.
    """

    #: Canonical set of content-type tab labels in priority order for probing.
    TABS: tuple[str, ...] = (
        "Specialties",
        "Firms & Products",
        "Articles",
        "Case Studies",
        "All",
    )

    def __init__(self, page: Page) -> None:
        self._page = page

        # ── Locators stored at construction time ─────────────────────────────
        # Handles three possible DOM implementations:
        #   role="tab"    — semantic ARIA tab widget
        #   role="button" — generic button used as tab
        #   text match    — plain text node with a click handler
        self.tab_all: Locator = self._tab_locator("All")
        self.tab_specialties: Locator = self._tab_locator("Specialties")
        self.tab_firms: Locator = self._tab_locator("Firms & Products")
        self.tab_articles: Locator = self._tab_locator("Articles")
        self.tab_case_studies: Locator = self._tab_locator("Case Studies")

    # ── Locator helpers ──────────────────────────────────────────────────────

    def _tab_locator(self, name: str) -> Locator:
        """
        Build a chained locator that matches ``name`` across all known
        tab implementations (role=tab, role=button, or plain text).
        """
        return (
            self._page.get_by_role("tab", name=name)
            .or_(self._page.get_by_role("button", name=name))
            .or_(self._page.locator(f"text='{name}'").first)
        )

    # ── Queries ──────────────────────────────────────────────────────────────

    def first_available_tab(self) -> str | None:
        """
        Return the label of the first content-type tab found in the DOM,
        or ``None`` if no tabs are rendered.
        """
        for name in self.TABS:
            if self._tab_locator(name).count() > 0:
                return name
        return None

    def available_tabs(self) -> list[str]:
        """Return labels of all content-type tabs currently in the DOM."""
        return [name for name in self.TABS if self._tab_locator(name).count() > 0]

    # ── Actions ──────────────────────────────────────────────────────────────

    def click_tab(self, name: str) -> None:
        """Click the tab with the given label and wait for the page to settle."""
        self._tab_locator(name).click()
        self._page.wait_for_load_state("networkidle")

    def click_first_available(self) -> str:
        """
        Click the first available tab.

        Returns
        -------
        str
            Label of the tab that was clicked.

        Raises
        ------
        LookupError
            If no content-type tabs are found on the page.
        """
        name = self.first_available_tab()
        if name is None:
            raise LookupError("No content-type filter tabs found on the page.")
        self.click_tab(name)
        return name
