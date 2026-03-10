"""
Navigation tests — tests/ui/test_navigation.py
================================================
Verifies that clicking NavigationBar links loads the correct pages.

Tests
-----
1. Reports nav link changes URL to /grit.
2. Insights nav link changes URL to /insights.
3. Events nav link changes URL to /events.
4. Events page title updates to reflect the section (retried via expect()).
"""

import re

import pytest
from playwright.sync_api import expect

from tests.ui.pages.home_page import HomePage


@pytest.mark.ui
def test_reports_nav_link_changes_url(page, base_url: str) -> None:
    """Clicking Reports (the <nav> link) must navigate to the /grit path."""
    home = HomePage(page, base_url)
    home.navigate()
    home.nav_bar.go_to_reports()

    assert "grit" in page.url.lower(), (
        f"Expected URL to contain 'grit' after clicking Reports; got: {page.url!r}"
    )


@pytest.mark.ui
def test_insights_nav_link_changes_url(page, base_url: str) -> None:
    """Clicking Insights must update the browser URL to contain 'insights'."""
    home = HomePage(page, base_url)
    home.navigate()
    home.nav_bar.go_to_insights()

    assert "insights" in page.url.lower(), (
        f"Expected URL to contain 'insights'; got: {page.url!r}"
    )


@pytest.mark.ui
def test_events_nav_link_changes_url(page, base_url: str) -> None:
    """Clicking Events must update the browser URL to contain 'events'."""
    home = HomePage(page, base_url)
    home.navigate()
    home.nav_bar.go_to_events()

    assert "events" in page.url.lower(), (
        f"Expected URL to contain 'events'; got: {page.url!r}"
    )


@pytest.mark.ui
def test_events_page_title_reflects_section(page, base_url: str) -> None:
    """
    After navigating to /events the document title must mention 'events'.

    Next.js updates <title> asynchronously after a client-side route change.
    ``expect().to_have_title()`` retries until the title matches or times out,
    avoiding the race condition of reading ``page.title()`` immediately.
    """
    home = HomePage(page, base_url)
    home.navigate()
    home.nav_bar.go_to_events()

    assert "events" in page.url.lower(), (
        f"URL does not contain 'events' after navigation; got: {page.url!r}"
    )
    expect(page).to_have_title(re.compile(r"event", re.IGNORECASE), timeout=10_000)
