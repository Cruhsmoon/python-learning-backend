"""
UI test fixtures
================
Provides:
  base_url              — read from BASE_URL_UI env var (falls back to live site).
  browser_context_args  — viewport + https-error tolerance for CI.
"""

import os

import pytest


@pytest.fixture(scope="session")
def base_url() -> str:  # type: ignore[override]
    """
    Base URL injected into every Page Object.

    Source (in priority order):
      1. BASE_URL_UI environment variable
      2. Hard-coded fallback to the live Greenbook website

    Strip trailing slash so Page Objects can safely append paths.
    """
    url = os.getenv("BASE_URL_UI", "https://www.greenbook.org")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """
    Merge project-level browser context settings on top of whatever
    pytest-playwright provides by default.

    viewport          — consistent 1280×800 window for all UI tests.
    ignore_https_errors — tolerate self-signed certs in staging environments.
    """
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 800},
        "ignore_https_errors": True,
    }
