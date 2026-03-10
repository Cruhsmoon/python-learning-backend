"""BasePage — shared foundation for all Page Objects."""

from __future__ import annotations

from playwright.sync_api import Page


class BasePage:

    """
    Minimal base class shared by every Page Object.

    Attributes
    ----------
    page : Page
        The Playwright Page instance (public so subclasses and tests can use it).
    base_url : str
        Base URL without a trailing slash.
    """

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")

    # ── Navigation ───────────────────────────────────────────────────────────

    def navigate_to(self, path: str = "/") -> None:
        """Go to ``base_url + path`` and wait until the network is idle."""
        self.page.goto(self.base_url + path)
        self.page.wait_for_load_state("networkidle")

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def current_url(self) -> str:
        return self.page.url

    @property
    def page_title(self) -> str:
        return self.page.title()
