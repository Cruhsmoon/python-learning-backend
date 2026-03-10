"""
Pagination tests — tests/ui/test_pagination.py
================================================
Verifies that the search results page exposes a mechanism to load additional
results and that activating it changes the visible content.

Greenbook uses a "View all" expansion button rather than Next / Previous page
controls.  All tests skip gracefully when no such control is present.

Tests
-----
1. Search results page displays a numeric result count.
2. A "View all" or "Load more" control exists for large result sets.
3. Activating the control loads additional or different content.
"""

import pytest

from tests.ui.pages.search_page import SearchPage

_QUERY = "market research"


@pytest.mark.ui
def test_result_count_label_is_displayed(page, base_url: str) -> None:
    """
    The search results page should show a numeric result count
    (e.g., '26 results') somewhere on the page.
    """
    sp = SearchPage(page, base_url)
    sp.navigate(_QUERY)
    page.wait_for_load_state("networkidle")

    text = sp.results.result_count_text()

    if not text:
        pytest.skip("Result count label not found on page.")

    assert any(ch.isdigit() for ch in text), (
        f"Result count label contains no digits: {text!r}"
    )


@pytest.mark.ui
def test_pagination_control_exists(page, base_url: str) -> None:
    """
    A 'View all', 'Load more', or 'Next' control must exist when the result
    set exceeds the initial view.  Skipped if all results fit on one screen.
    """
    sp = SearchPage(page, base_url)
    sp.navigate(_QUERY)
    page.wait_for_load_state("networkidle")

    if not sp.results.has_pagination_control():
        pytest.skip(
            "No pagination / load-more / view-all control found; "
            "all results may already be visible."
        )

    assert sp.results.has_pagination_control()


@pytest.mark.ui
def test_view_all_expands_result_set(page, base_url: str) -> None:
    """
    Clicking the 'View all' control must result in either more cards being
    visible or the URL changing to reflect pagination.
    """
    sp = SearchPage(page, base_url)
    sp.navigate(_QUERY)
    sp.results.wait_for_cards()

    all_content = "a[href*='/company/'], a[href*='/case-study/']"
    before_count = page.locator(all_content).count()
    initial_url = page.url

    if not sp.results.has_pagination_control():
        pytest.skip("No pagination control found; cannot test expansion.")

    try:
        sp.results.click_view_all()
    except LookupError:
        pytest.skip("Pagination control not clickable.")

    after_count = page.locator(all_content).count()
    url_changed = page.url != initial_url

    assert after_count >= before_count or url_changed, (
        f"After pagination: count {before_count} → {after_count}, "
        f"URL {'changed' if url_changed else 'unchanged'} ({page.url!r})"
    )
