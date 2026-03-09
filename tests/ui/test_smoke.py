"""
Smoke tests — tests/ui/test_smoke.py
=====================================
Fast baseline checks that confirm the Greenbook homepage is reachable,
correctly branded, and has its main navigation intact.

Scenarios:
  1. Page title contains "Greenbook".
  2. Main <nav> element is visible.
  3. Navigation bar contains expected destination links.
"""

import re

import pytest

from tests.ui.pages.home_page import HomePage


@pytest.mark.ui
def test_homepage_title_contains_greenbook(page, base_url: str) -> None:
    """Page title must identify the Greenbook brand."""
    home = HomePage(page, base_url)
    home.navigate()

    assert re.search(r"greenbook", home.page_title, re.IGNORECASE), (
        f"Expected 'Greenbook' in page title, got: {home.page_title!r}"
    )


@pytest.mark.ui
def test_main_navigation_is_visible(page, base_url: str) -> None:
    """A <nav> / [role='navigation'] landmark must be present and visible."""
    home = HomePage(page, base_url)
    home.navigate()

    assert home.nav.is_visible(), (
        "Main navigation element is not visible on the Greenbook homepage."
    )


@pytest.mark.ui
def test_navigation_contains_key_destinations(page, base_url: str) -> None:
    """Core site sections (Events, Insights) must appear as nav links."""
    home = HomePage(page, base_url)
    home.navigate()

    texts = [t.strip().lower() for t in home.nav_link_texts() if t.strip()]
    expected = {"events", "insights"}

    missing = [label for label in expected if not any(label in t for t in texts)]
    assert not missing, (
        f"Nav links not found: {missing}. Visible nav texts: {texts}"
    )
