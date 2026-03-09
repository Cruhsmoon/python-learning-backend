"""
BasePage
========
Shared base class for all Page Objects.

Provides:
  - Consistent navigation with networkidle wait.
  - `current_url` and `page_title` convenience properties.
"""

from __future__ import annotations

from playwright.sync_api import Page


class BasePage:
    """Minimal shared base for every Page Object in this project."""

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")

    # ── Navigation ───────────────────────────────────────────────────────────

    def navigate_to(self, path: str = "/") -> None:
        """Go to ``base_url + path`` and wait until network is idle."""
        self.page.goto(self.base_url + path)
        self.page.wait_for_load_state("networkidle")

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def current_url(self) -> str:
        return self.page.url

    @property
    def page_title(self) -> str:
        return self.page.title()
