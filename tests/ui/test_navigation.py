"""
Navigation tests — tests/ui/test_navigation.py
================================================
Verifies that clicking main navigation links loads the correct pages.

Scenarios:
  1. Clicking Events / Insights updates the browser URL (parametrized).
  2. The Events page title confirms the correct section loaded.
  3. URL changes after clicking any nav link (content changed).
"""

import pytest

from tests.ui.pages.home_page import HomePage

# (nav href, fragment expected in the resulting URL)
_NAV_CASES = [
    ("/events", "events"),
    ("/insights", "insights"),
]


@pytest.mark.ui
@pytest.mark.parametrize("href,expected_fragment", _NAV_CASES)
def test_nav_link_updates_url(page, base_url: str, href: str, expected_fragment: str) -> None:
    """Clicking a nav link must update the browser URL to contain the target path."""
    home = HomePage(page, base_url)
    home.navigate()
    home.click_nav_link(href)

    assert expected_fragment in page.url.lower(), (
        f"Expected URL to contain '{expected_fragment}' after clicking nav link '{href}'; "
        f"got: {page.url!r}"
    )


@pytest.mark.ui
def test_events_page_title_reflects_section(page, base_url: str) -> None:
    """After navigating to /events the page title should include 'Events'."""
    home = HomePage(page, base_url)
    home.navigate()
    home.click_nav_link("/events")

    title = page.title()
    assert "event" in title.lower(), (
        f"Expected 'events' in page title after navigation to /events; got: {title!r}"
    )


@pytest.mark.ui
def test_navigation_changes_page_url(page, base_url: str) -> None:
    """Navigating to Insights must produce a URL different from the homepage."""
    home = HomePage(page, base_url)
    home.navigate()
    initial_url = page.url

    home.click_nav_link("/insights")

    assert page.url != initial_url, (
        "URL did not change after clicking the Insights navigation link."
    )
