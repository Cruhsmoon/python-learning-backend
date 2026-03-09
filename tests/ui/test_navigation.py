"""
Navigation tests — tests/ui/test_navigation.py
================================================
Verifies that clicking main navigation links loads the correct pages.

Scenarios:
  1. Clicking Events / Insights updates the browser URL (parametrized).
  2. The Events page title confirms the correct section loaded.
  3. URL changes after clicking any nav link (content changed).
"""

import re

import pytest
from playwright.sync_api import expect

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
    """
    After navigating to /events the URL and document title must confirm
    the events section loaded.

    Next.js updates <title> asynchronously after a client-side route change.
    Reading page.title() immediately after navigation may return the previous
    page's title.  We use Playwright's expect().to_have_title() which retries
    internally until the title matches or the timeout expires.
    """
    home = HomePage(page, base_url)
    home.navigate()
    home.click_nav_link("/events")

    assert "events" in page.url.lower(), (
        f"Expected URL to contain 'events' after navigation; got: {page.url!r}"
    )

    # Retry-able assertion — waits up to 10 s for the title to update.
    expect(page).to_have_title(re.compile(r"event", re.IGNORECASE), timeout=10_000)


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
