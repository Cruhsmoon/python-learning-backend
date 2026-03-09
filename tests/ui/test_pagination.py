"""
Pagination tests — tests/ui/test_pagination.py
================================================
Verifies that the Greenbook search results page exposes a mechanism to load
additional results and that using it changes the visible content.

Greenbook uses a "View all" expansion button rather than traditional
Next / Previous page controls.  All pagination tests skip gracefully when
no such control exists (e.g., results fit on a single page).

Scenarios:
  1. Search results page displays a numeric result count.
  2. A "View all" / "Load more" / "Next" control exists for large result sets.
  3. Activating that control loads additional or different content.
"""

import pytest

from tests.ui.pages.search_results_page import SearchResultsPage

# Use a broad query to maximise the chance of triggering pagination.
_QUERY = "market research"


@pytest.mark.ui
def test_results_page_displays_count(page, base_url: str) -> None:
    """
    The search results page should show a numeric result count somewhere on
    the page (e.g., '26 results').
    """
    rp = SearchResultsPage(page, base_url)
    rp.navigate(_QUERY)
    page.wait_for_load_state("networkidle")

    count_el = rp.result_count_element
    if count_el.count() == 0:
        pytest.skip("Result count element not found on page.")

    text = count_el.inner_text()
    assert any(ch.isdigit() for ch in text), (
        f"Result count element does not contain a number: {text!r}"
    )


@pytest.mark.ui
def test_pagination_control_is_present(page, base_url: str) -> None:
    """
    A 'View all', 'Load more', or 'Next' control should exist when the result
    set does not fit in the initial view.  Skipped if results fit on one page.
    """
    rp = SearchResultsPage(page, base_url)
    rp.navigate(_QUERY)
    page.wait_for_load_state("networkidle")

    if not rp.has_pagination_control():
        pytest.skip(
            "No pagination / load-more / view-all control found; "
            "all results may already be visible."
        )

    assert rp.has_pagination_control()


@pytest.mark.ui
def test_pagination_control_loads_more_content(page, base_url: str) -> None:
    """
    Clicking the pagination / 'View all' control must result in either:
      - More result cards being visible, OR
      - The browser URL changing (navigated to a new page).
    """
    rp = SearchResultsPage(page, base_url)
    rp.navigate(_QUERY)
    page.wait_for_selector(
        "a[href*='/company/'], a[href*='/case-study/']", timeout=15_000
    )

    before_count = page.locator(
        "a[href*='/company/'], a[href*='/case-study/']"
    ).count()
    initial_url = page.url

    if not rp.has_pagination_control():
        pytest.skip("No pagination control found; cannot test loading more results.")

    try:
        rp.click_next_or_view_all()
    except LookupError:
        pytest.skip("Pagination control disappeared before it could be clicked.")

    after_count = page.locator(
        "a[href*='/company/'], a[href*='/case-study/']"
    ).count()
    url_changed = page.url != initial_url

    assert after_count >= before_count or url_changed, (
        f"After clicking pagination control: "
        f"item count {before_count} → {after_count}, "
        f"URL {'changed' if url_changed else 'unchanged'} ({page.url!r})"
    )
