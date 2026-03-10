"""
UI test fixtures and hooks
===========================
Provides:
  base_url              — read from BASE_URL_UI env var (falls back to live site).
  browser_context_args  — consistent viewport + HTTPS tolerance for CI.
  screenshot_on_failure — captures a full-page PNG for every failed UI test.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import Page


# ── Session-scoped fixtures ──────────────────────────────────────────────────

@pytest.fixture(scope="session")
def base_url() -> str:  # type: ignore[override]
    """
    Base URL for all UI tests.

    Resolution order:
      1. ``BASE_URL_UI`` environment variable.
      2. Hard-coded fallback to the live Greenbook website.
    """
    url = os.getenv("BASE_URL_UI", "https://www.greenbook.org")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """
    Merge project-level browser context options on top of defaults.

    ``viewport``           — consistent 1280 × 800 window for all tests.
    ``ignore_https_errors``— tolerate self-signed certs in staging environments.
    """
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 800},
        "ignore_https_errors": True,
    }


# ── Screenshot on failure ────────────────────────────────────────────────────

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> Generator:
    """
    Attach ``rep_<when>`` attributes to each test item so the
    ``screenshot_on_failure`` fixture can inspect the call outcome.
    """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(autouse=True)
def screenshot_on_failure(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    Automatically capture a full-page screenshot when a UI test fails.

    Screenshots are saved to ``screenshots/<safe_test_id>.png`` in the
    project root.  The fixture is a no-op for tests that do not use the
    ``page`` fixture (e.g., non-Playwright tests that may share this conftest
    scope transitively).
    """
    yield

    if not (hasattr(request.node, "rep_call") and request.node.rep_call.failed):
        return

    page: Page | None = request.node.funcargs.get("page")  # type: ignore[assignment]
    if page is None:
        return

    screenshot_dir = Path("screenshots")
    screenshot_dir.mkdir(exist_ok=True)

    # Sanitise the node ID to a safe filename.
    safe_name = re.sub(r"[^\w._-]", "_", request.node.nodeid)
    screenshot_path = screenshot_dir / f"{safe_name}.png"

    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:
        # Never let screenshot capture break the test run.
        pass
