"""
UI test fixtures and hooks
===========================
Provides:
  base_url              — read from BASE_URL_UI env var (falls back to live site).
  browser_context_args  — consistent viewport + HTTPS tolerance for CI.
  screenshot_on_failure — captures a full-page PNG; attaches to Allure + saves to disk.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Generator

import allure
import pytest
from playwright.sync_api import Page


@pytest.fixture(scope="session")
def base_url() -> str:  # type: ignore[override]
    url = os.getenv("BASE_URL_UI", "https://www.greenbook.org")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 800},
        "ignore_https_errors": True,
    }


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> Generator:
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(autouse=True)
def screenshot_on_failure(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    On UI test failure:
      1. Capture full-page screenshot bytes.
      2. Attach to Allure report (survives in CI artifacts).
      3. Also save to screenshots/ on disk for local debugging.
    """
    yield

    if not (hasattr(request.node, "rep_call") and request.node.rep_call.failed):
        return

    page: Page | None = request.node.funcargs.get("page")  # type: ignore[assignment]
    if page is None:
        return

    try:
        screenshot_bytes = page.screenshot(full_page=True)
    except Exception:
        return

    # Allure attachment (primary)
    allure.attach(
        screenshot_bytes,
        name="Screenshot on failure",
        attachment_type=allure.attachment_type.PNG,
    )

    # Disk save (secondary — local debugging)
    screenshot_dir = Path("screenshots")
    screenshot_dir.mkdir(exist_ok=True)
    safe_name = re.sub(r"[^\w._-]", "_", request.node.nodeid)
    try:
        (screenshot_dir / f"{safe_name}.png").write_bytes(screenshot_bytes)
    except Exception:
        pass
