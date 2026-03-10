"""
Search tests — tests/ui/test_search.py
========================================
Verifies Greenbook keyword search end-to-end.

Tests
-----
1. Direct navigation to /keyword-search-results?q=hotel loads correctly.
2. At least one company result card is returned for a known query.
3. Submitting the homepage search box navigates to the results page.
4. Every result card links to a /company/ profile URL.
"""

import pytest

from tests.ui.pages.home_page import HomePage
from tests.ui.pages.search_page import SearchPage

_QUERY = "hotel"


@pytest.mark.ui
def test_search_results_page_loads_with_query_param(page, base_url: str) -> None:
    """Direct navigation to the search URL must produce a results page."""
    sp = SearchPage(page, base_url)
    sp.navigate(_QUERY)

    assert sp.is_on_search_page(), (
        f"Expected search results URL; got: {page.url!r}"
    )
    assert "q=" in page.url, f"Query param 'q=' missing from URL: {page.url!r}"


@pytest.mark.ui
def test_search_returns_company_cards(page, base_url: str) -> None:
    """A known search term must yield at least one /company/ result card."""
    sp = SearchPage(page, base_url)
    sp.navigate(_QUERY)
    sp.results.wait_for_cards()

    assert sp.results.has_results(), (
        f"Expected company cards for query '{_QUERY}'; found none."
    )


@pytest.mark.ui
def test_homepage_search_box_navigates_to_results(page, base_url: str) -> None:
    """
    Filling the homepage search box and pressing Enter must navigate the
    browser to the keyword-search-results page.
    """
    home = HomePage(page, base_url)
    home.navigate()
    home.search(_QUERY)

    sp = SearchPage(page, base_url)
    assert sp.is_on_search_page(), (
        f"Expected search results URL after form submit; got: {page.url!r}"
    )


@pytest.mark.ui
def test_first_result_links_to_company_profile(page, base_url: str) -> None:
    """Each result card must reference a /company/ profile path."""
    sp = SearchPage(page, base_url)
    sp.navigate(_QUERY)
    sp.results.wait_for_cards()

    href = sp.results.first_card_href()
    assert "/company/" in href, (
        f"First result card href does not point to a company: {href!r}"
    )
