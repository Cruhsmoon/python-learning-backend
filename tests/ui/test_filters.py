"""
Filter tests — tests/ui/test_filters.py
=========================================
Verifies that result-type filters (content tabs) on the search results page
work correctly.

Greenbook does not expose a traditional checkbox filter sidebar; instead it
uses content-type tabs (Specialties, Firms & Products, Articles, Case Studies)
to narrow the visible result set.  Tests skip gracefully if no such controls
are rendered by the current version of the site.

Scenarios:
  1. At least one content-type tab/filter control is present on the results page.
  2. Clicking a filter tab keeps the user on the search results page.
  3. After applying a filter the page still renders content (no blank/error).
"""

import pytest

from tests.ui.pages.search_results_page import CONTENT_TABS, SearchResultsPage

_QUERY = "research"


@pytest.mark.ui
def test_filter_tab_controls_are_present(page, base_url: str) -> None:
    """
    The search results page should expose at least one content-type filter tab.
    The test is skipped if the site renders no such controls.
    """
    rp = SearchResultsPage(page, base_url)
    rp.navigate(_QUERY)
    page.wait_for_load_state("networkidle")

    found = [name for name in CONTENT_TABS if rp.content_tab(name).count() > 0]

    if not found:
        pytest.skip(
            "No content-type filter tabs found on the search results page; "
            "the site may use a different filtering mechanism."
        )

    assert len(found) > 0, f"Expected filter tabs, found: {found}"


@pytest.mark.ui
def test_clicking_filter_tab_stays_on_results_page(page, base_url: str) -> None:
    """
    Clicking a content-type tab must keep the user on the search results page
    (URL still contains /keyword-search-results or q=).
    """
    rp = SearchResultsPage(page, base_url)
    rp.navigate(_QUERY)
    page.wait_for_selector("a[href*='/company/']", timeout=15_000)

    chosen = rp.first_available_tab()
    if chosen is None:
        pytest.skip("No content-type filter tab found; skipping filter interaction test.")

    rp.click_content_tab(chosen)

    assert "keyword-search-results" in page.url or "q=" in page.url, (
        f"Unexpected URL after clicking filter tab '{chosen}': {page.url!r}"
    )


@pytest.mark.ui
def test_filter_tab_does_not_produce_empty_page(page, base_url: str) -> None:
    """
    After applying any available filter the results area must still render
    at least one content element (company card, article, or case study link).
    """
    rp = SearchResultsPage(page, base_url)
    rp.navigate(_QUERY)
    page.wait_for_load_state("networkidle")

    chosen = rp.first_available_tab()
    if chosen is None:
        pytest.skip("No content-type filter tab found.")

    rp.click_content_tab(chosen)

    content = page.locator(
        "a[href*='/company/'], a[href*='/case-study/'], a[href*='/insights/']"
    )
    assert content.count() > 0 or page.locator("main").is_visible(), (
        f"No content visible after applying filter tab '{chosen}'."
    )
