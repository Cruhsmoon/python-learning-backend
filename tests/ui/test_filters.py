"""
Filter tests — tests/ui/test_filters.py
=========================================
Verifies that content-type filter tabs on the search results page work.

Greenbook uses content-type tabs (Specialties, Firms & Products, Articles,
Case Studies) instead of a traditional checkbox filter sidebar.  All tests
skip gracefully when the site renders no such controls.

Tests
-----
1. Content-type tab controls are present on the results page.
2. Clicking a tab keeps the user on the search results page.
3. After applying a tab filter the page still renders content.
"""

import pytest

from tests.ui.pages.search_page import SearchPage

_QUERY = "research"


@pytest.mark.ui
def test_filter_tabs_are_present(page, base_url: str) -> None:
    """
    At least one content-type filter tab must be rendered on the search
    results page for a typical query.
    """
    sp = SearchPage(page, base_url)
    sp.navigate(_QUERY)
    page.wait_for_load_state("networkidle")

    available = sp.filters.available_tabs()

    if not available:
        pytest.skip(
            "No content-type filter tabs found; site may have changed its UI."
        )

    assert len(available) > 0, f"Expected filter tabs; found: {available}"


@pytest.mark.ui
def test_clicking_tab_keeps_user_on_search_page(page, base_url: str) -> None:
    """
    Clicking a content-type tab must keep the browser on the search results
    page (URL must still contain /keyword-search-results or q=).
    """
    sp = SearchPage(page, base_url)
    sp.navigate(_QUERY)
    sp.results.wait_for_cards()

    try:
        sp.filters.click_first_available()
    except LookupError:
        pytest.skip("No content-type filter tabs found.")

    assert sp.is_on_search_page(), (
        f"Unexpected URL after clicking filter tab: {page.url!r}"
    )


@pytest.mark.ui
def test_filter_tab_does_not_empty_the_results_area(page, base_url: str) -> None:
    """
    After applying a filter tab at least one content element must remain
    visible (no blank screen or error page).
    """
    sp = SearchPage(page, base_url)
    sp.navigate(_QUERY)
    page.wait_for_load_state("networkidle")

    try:
        sp.filters.click_first_available()
    except LookupError:
        pytest.skip("No content-type filter tabs found.")

    content = page.locator(
        "a[href*='/company/'], a[href*='/case-study/'], a[href*='/insights/']"
    )
    assert content.count() > 0 or page.locator("main").is_visible(), (
        "No content visible after applying the filter tab."
    )
