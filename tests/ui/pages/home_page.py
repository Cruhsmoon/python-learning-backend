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

        Live site: <input type="search" placeholder="Find suppliers, articles, …">
        """
        for candidate in (
            self.page.locator("input[type='search']"),
            self.page.get_by_role("searchbox"),
            self.page.locator("input[name='q']"),
            self.page.locator("input[placeholder*='Find suppliers' i]"),
            self.page.locator("input[placeholder*='Search' i]"),
        ):
            if candidate.count() > 0:
                return candidate.first
        return self.page.locator("input[type='text']").first

    # ── Actions ──────────────────────────────────────────────────────────────

    def search(self, query: str) -> None:
        """
        Fill the search input and press Enter.

        Greenbook uses client-side routing (Next.js), so a full-page reload
        never fires.  We wait for the URL to change to keyword-search-results
        instead of relying on networkidle alone.
        """
        inp = self.search_input
        inp.wait_for(state="visible", timeout=10_000)
        inp.fill(query)
        inp.press("Enter")
        # Wait for React/Next.js router to commit the navigation.
        self.page.wait_for_url("**/keyword-search-results**", timeout=10_000)

    def click_nav_link(self, href: str) -> None:
        """
        Click the most reliable link for *href* and wait for navigation.

        Greenbook's page contains multiple <a> elements for the same href:
          • Mega-menu cards (large text, collapsed dropdown, click does nothing)
          • Footer / inline links (short text, always visible, reliable)

        Strategy:
          1. Collect all matching <a> tags.
          2. Sort by inner-text length — shorter = footer/nav link, not a card.
          3. Scroll each into view and click; accept the first one whose click
             actually changes the URL (detected via wait_for_url with
             wait_until="commit" which works for Next.js pushState routing).
        """
        links = sorted(
            self.page.locator(f"a[href='{href}']").all(),
            key=lambda lnk: len(lnk.inner_text()),
        )
        if not links:
            raise LookupError(f"No <a href='{href}'> found on the page.")

        for link in links:
            link.scroll_into_view_if_needed()
            link.click()
            try:
                # "commit" fires as soon as the URL is committed (pushState),
                # before the new page finishes loading — ideal for SPA routing.
                self.page.wait_for_url(f"**{href}**", timeout=4_000, wait_until="commit")
                self.page.wait_for_load_state("networkidle")
                return
            except Exception:
                # This candidate did not trigger navigation; try the next one.
                continue

        raise LookupError(
            f"Clicked {len(links)} candidate link(s) for href='{href}' "
            "but none produced a URL change."
        )

    def nav_link_texts(self) -> list[str]:
        """
        Return the first-line text of primary site-destination links.

        Because the nav links are scattered across the page, we probe by
        known hrefs and take only the first line of each link's text so
        mega-menu card descriptions are excluded.
        """
        results: list[str] = []
        seen: set[str] = set()
        for a in self.page.locator(
            "a[href='/events'], a[href='/insights'], a[href='/grit'], "
            "a[href='/for-suppliers'], a[href='/find-market-research']"
        ).all():
            first_line = a.inner_text().strip().split("\n")[0].strip()
            key = first_line.lower()
            if first_line and key not in seen:
                seen.add(key)
                results.append(first_line)
        return results
