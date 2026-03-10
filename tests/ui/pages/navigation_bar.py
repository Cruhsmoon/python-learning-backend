"""NavigationBar — site-wide navigation Page Object."""

from __future__ import annotations

from playwright.sync_api import Locator, Page


class NavigationBar:
    """
    Encapsulates every action and locator related to site navigation.

    DOM reality (verified against live site):
    - The ``<nav>`` element contains only the "Reports" (/grit) link.
    - Events and Insights links live outside <nav> as plain <a> tags.
    - Some links are inside collapsed mega-menu cards and never trigger
      navigation on click; shorter-text variants (footer links) are reliable.

    All public ``go_to_*`` methods hide this complexity from test authors.
    """

    def __init__(self, page: Page, base_url: str) -> None:
        self._page = page
        self._base_url = base_url.rstrip("/")

        # ── Locators stored at construction time ─────────────────────────────
        # Scope to <nav> to avoid matching the mega-menu card link with the
        # same text — the nav element contains exactly one /grit anchor.
        self.reports_link: Locator = page.locator("nav a[href='/grit']").first

        # Insights: filter to the short "Insights" text variant, not the
        # mega-menu card ("Expert Articles\n\n…").
        self.insights_link: Locator = (
            page.locator("a[href='/insights']").filter(has_text="Insights")
        )

        # Events: "In-person" is the plain footer link that actually navigates;
        # "Global Conferences\n\n…" is a mega-menu card that does not.
        self.events_link: Locator = (
            page.locator("a[href='/events']").filter(has_text="In-person")
        )

    # ── High-level actions ───────────────────────────────────────────────────

    def go_to_reports(self) -> None:
        """Navigate to the Reports (GRIT) section."""
        self._navigate_by_href("/grit")

    def go_to_insights(self) -> None:
        """Navigate to the Insights section."""
        self._navigate_by_href("/insights")

    def go_to_events(self) -> None:
        """Navigate to the Events section."""
        self._navigate_by_href("/events")

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _navigate_by_href(self, href: str) -> None:
        """
        Click the most reliable <a href="{href}"> on the page.

        Strategy: sort all matching links by inner-text length (shortest first).
        Shorter text = footer/nav link; longer text = mega-menu card.
        Try each candidate with ``wait_until="commit"`` (fires on pushState).
        """
        links = sorted(
            self._page.locator(f"a[href='{href}']").all(),
            key=lambda lnk: len(lnk.inner_text()),
        )
        if not links:
            raise LookupError(f"No <a href='{href}'> found on the page.")

        for link in links:
            link.scroll_into_view_if_needed()
            link.click()
            try:
                self._page.wait_for_url(
                    f"**{href}**", timeout=5_000, wait_until="commit"
                )
                self._page.wait_for_load_state("networkidle")
                return
            except Exception:
                continue  # try next candidate

        raise LookupError(
            f"Clicked {len(links)} link(s) for href='{href}' but none "
            "produced a URL change."
        )
