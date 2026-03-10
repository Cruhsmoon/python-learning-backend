"""
Smoke tests — tests/ui/test_smoke.py
======================================
Fast baseline checks that confirm the Greenbook homepage is reachable,
correctly branded, and exposes the expected navigation structure.

Tests
-----
1. Homepage title contains "Greenbook".
2. Main <nav> navigation landmark is visible.
3. Links to core site sections (Events, Insights) are present.
"""

import pytest

from tests.ui.pages.home_page import HomePage


@pytest.mark.ui
def test_homepage_title_contains_greenbook(page, base_url: str) -> None:
    """Page title must identify the Greenbook brand."""
    home = HomePage(page, base_url)
    home.navigate()

    assert "greenbook" in home.page_title.lower(), (
        f"Expected 'Greenbook' in page title; got: {home.page_title!r}"
    )


@pytest.mark.ui
def test_main_navigation_landmark_is_visible(page, base_url: str) -> None:
    """A <nav> landmark must be present and visible on the homepage."""
    home = HomePage(page, base_url)
    home.navigate()

    assert home.is_nav_visible(), (
        "Main <nav> element is not visible on the Greenbook homepage."
    )


@pytest.mark.ui
def test_homepage_has_links_to_core_sections(page, base_url: str) -> None:
    """
    Links to core site destinations must be reachable from the homepage.

    Greenbook's primary nav links live outside the <nav> element, so we
    assert by href presence rather than by nav-container text.
    """
    home = HomePage(page, base_url)
    home.navigate()

    missing = [
        href for href in ("/events", "/insights")
        if not home.has_link_to(href)
    ]
    assert not missing, f"Homepage is missing links to: {missing}"
