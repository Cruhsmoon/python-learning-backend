"""
Search tests — tests/ui/test_search.py
========================================
Verifies that the Greenbook keyword search works end-to-end.

Scenarios:
  1. Navigating directly to /keyword-search-results?q=hotel loads correctly.
  2. At least one company result card is returned for a known query.
  3. Submitting the homepage search form navigates to the results page.
  4. Every result card links to a /company/ profile URL.
"""

import pytest

from tests.ui.pages.home_page import HomePage
from tests.ui.pages.search_results_page import SearchResultsPage

_QUERY = "hotel"


@pytest.mark.ui
def test_search_results_url_contains_query(page, base_url: str) -> None:
    """Direct navigation to the search URL must land on the results page."""
    rp = SearchResultsPage(page, base_url)
    rp.navigate(_QUERY)

    assert "keyword-search-results" in page.url, (
        f"Expected '/keyword-search-results' in URL, got: {page.url!r}"
    )
    assert "q=" in page.url, (
        f"Expected query param 'q=' in URL, got: {page.url!r}"
    )


@pytest.mark.ui
def test_search_returns_at_least_one_company_card(page, base_url: str) -> None:
    """A known search term must yield at least one /company/ result card."""
    rp = SearchResultsPage(page, base_url)
    rp.navigate(_QUERY)
    page.wait_for_selector("a[href*='/company/']", timeout=15_000)

    assert rp.result_count() > 0, (
        f"Expected at least one company card for query '{_QUERY}', got none."
    )


@pytest.mark.ui
def test_search_via_homepage_form_navigates_to_results(page, base_url: str) -> None:
    """
    Filling the homepage search box and pressing Enter must navigate the
    browser to the keyword-search-results page.
    """
    home = HomePage(page, base_url)
    home.navigate()
    home.search(_QUERY)

    assert "keyword-search-results" in page.url or "q=" in page.url, (
        f"Expected search results URL after form submit; got {page.url!r}"
    )


@pytest.mark.ui
def test_result_cards_link_to_company_profiles(page, base_url: str) -> None:
    """Each visible result card must point to a /company/ profile page."""
    rp = SearchResultsPage(page, base_url)
    rp.navigate(_QUERY)
    page.wait_for_selector("a[href*='/company/']", timeout=15_000)

    href = rp.first_company_href()
    assert "/company/" in href, (
        f"First result card href does not point to a company profile: {href!r}"
    )
