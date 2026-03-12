"""
Smoke tests — tests/ui/test_smoke.py
======================================
Fast baseline checks that confirm the Greenbook homepage is reachable,
correctly branded, and exposes the expected navigation structure.
"""

import allure
import pytest

from tests.ui.pages.home_page import HomePage


@allure.feature("UI — Homepage")
@allure.story("Brand identity")
@pytest.mark.ui
def test_homepage_title_contains_greenbook(page, base_url: str) -> None:
    """Page title must identify the Greenbook brand."""
    with allure.step(f"Navigate to {base_url}"):
        home = HomePage(page, base_url)
        home.navigate()
    with allure.step("Assert 'greenbook' in page title"):
        assert "greenbook" in home.page_title.lower(), (
            f"Expected 'Greenbook' in page title; got: {home.page_title!r}"
        )


@allure.feature("UI — Homepage")
@allure.story("Navigation structure")
@pytest.mark.ui
def test_main_navigation_landmark_is_visible(page, base_url: str) -> None:
    """A <nav> landmark must be present and visible on the homepage."""
    with allure.step(f"Navigate to {base_url}"):
        home = HomePage(page, base_url)
        home.navigate()
    with allure.step("Assert <nav> is visible"):
        assert home.is_nav_visible(), (
            "Main <nav> element is not visible on the Greenbook homepage."
        )


@allure.feature("UI — Homepage")
@allure.story("Navigation structure")
@pytest.mark.ui
def test_homepage_has_links_to_core_sections(page, base_url: str) -> None:
    """
    Links to /events, /insights, and /careers must be reachable from the homepage.

    REGRESSION: /careers was added to the navigation spec in sprint-14 but
    has not yet been deployed to the live site.  This test is intentionally
    failing to track the missing implementation.  Do NOT fix this test until
    the /careers route is live on www.greenbook.org.
    """
    with allure.step(f"Navigate to {base_url}"):
        home = HomePage(page, base_url)
        home.navigate()
        allure.attach(
            page.screenshot(full_page=True),
            name="Homepage screenshot",
            attachment_type=allure.attachment_type.PNG,
        )
    with allure.step("Assert links to /events, /insights, and /careers exist"):
        missing = [
            href for href in ("/events", "/insights", "/careers")
            if not home.has_link_to(href)
        ]
        assert not missing, (
            f"Homepage is missing links to: {missing}\n"
            f"Sprint-14 requirement: navigation bar must expose /careers."
        )
