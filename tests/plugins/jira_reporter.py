"""
Jira bug reporter — tests/plugins/jira_reporter.py
====================================================
Automatically creates a Jira Bug when a test fails.

Before filing a new issue, JiraContextCollector queries Jira Cloud to:
  - check for an exact fingerprint match (dedup)
  - search for similar bugs by file, exception type, and HTTP endpoint
  - fetch recent comments on matched issues
  - return a compact JSON context ready for LLM-based analysis

For UI (Playwright) tests the full-page screenshot saved by
screenshot_on_failure is attached to the Jira issue.

Activation
----------
    JIRA_REPORT_FAILURES=1 pytest ...

Configuration (via .env.jira or environment variables)
-------------------------------------------------------
    JIRA_URL           – https://<your-site>.atlassian.net
    JIRA_USERNAME      – your Atlassian account email
    JIRA_API_TOKEN     – Atlassian API token
    JIRA_PROJECT_KEY   – Project key (default: KAN)
    JIRA_BUG_TYPE_ID   – Issue type ID for Bug (default: 10010)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import textwrap
from pathlib import Path
from typing import Any

import allure
import httpx
import pytest

from tests.plugins.jira_context import JiraContextCollector


# ── Load .env.jira if present ─────────────────────────────────────────────────

def _load_env_file(path: str) -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file(str(Path(__file__).parent.parent.parent / ".env.jira"))


# ── Screenshot path helper ────────────────────────────────────────────────────

_SCREENSHOT_DIR = Path("screenshots")


def _screenshot_path_for(nodeid: str) -> Path | None:
    safe_name = re.sub(r"[^\w._-]", "_", nodeid)
    p = _SCREENSHOT_DIR / f"{safe_name}.png"
    return p if p.exists() else None


# ── Jira REST client ──────────────────────────────────────────────────────────

class _JiraClient:
    def __init__(self) -> None:
        self.base_url = os.environ["JIRA_URL"].rstrip("/")
        self.project_key = os.environ.get("JIRA_PROJECT_KEY", "KAN")
        self.bug_type_id = os.environ.get("JIRA_BUG_TYPE_ID", "10010")
        auth = (os.environ["JIRA_USERNAME"], os.environ["JIRA_API_TOKEN"])
        self._client = httpx.Client(auth=auth, timeout=15)

    def _api(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        # Inject JSON headers for every regular API call
        headers = kwargs.pop("headers", {})
        headers.setdefault("Accept", "application/json")
        headers.setdefault("Content-Type", "application/json")
        resp = self._client.request(
            method, f"{self.base_url}/rest/api/3{path}", headers=headers, **kwargs
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def create_bug(self, summary: str, description_adf: dict, labels: list[str]) -> str:
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "issuetype": {"id": self.bug_type_id},
                "summary": summary,
                "description": description_adf,
                "labels": labels,
            }
        }
        return self._api("POST", "/issue", content=json.dumps(payload))["key"]

    def add_comment(self, issue_key: str, body_text: str) -> None:
        payload = {
            "body": {
                "type": "doc", "version": 1,
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": body_text}],
                }],
            }
        }
        self._api("POST", f"/issue/{issue_key}/comment", content=json.dumps(payload))

    def attach_screenshot(self, issue_key: str, path: Path) -> None:
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/attachments"
        with path.open("rb") as f:
            # No Content-Type header here — httpx sets the correct
            # multipart/form-data boundary automatically via `files=`.
            resp = self._client.post(
                url,
                headers={"X-Atlassian-Token": "no-check", "Accept": "application/json"},
                files={"file": (path.name, f, "image/png")},
            )
        resp.raise_for_status()

    def close(self) -> None:
        self._client.close()


# ── ADF description builder ───────────────────────────────────────────────────

def _adf_doc(*blocks) -> dict:
    return {"type": "doc", "version": 1, "content": list(blocks)}

def _adf_heading(text: str, level: int = 2) -> dict:
    return {"type": "heading", "attrs": {"level": level},
            "content": [{"type": "text", "text": text}]}

def _adf_paragraph(text: str) -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}

def _adf_code_block(code: str, language: str = "text") -> dict:
    return {"type": "codeBlock", "attrs": {"language": language},
            "content": [{"type": "text", "text": code}]}


def _build_description(nodeid: str, longrepr: str, has_screenshot: bool) -> dict:
    truncated = textwrap.shorten(longrepr, width=10_000, placeholder="\n…(truncated)")
    blocks = [
        _adf_heading("Test Information", level=2),
        _adf_paragraph(f"Test: {nodeid}"),
        _adf_heading("Failure Details", level=2),
        _adf_code_block(truncated, language="text"),
        _adf_heading("How to Reproduce", level=2),
        _adf_paragraph(f"pytest {nodeid}"),
    ]
    if has_screenshot:
        blocks += [
            _adf_heading("Screenshot", level=2),
            _adf_paragraph("A full-page screenshot is attached to this issue."),
        ]
    return _adf_doc(*blocks)


# ── Pytest plugin ─────────────────────────────────────────────────────────────

_FAILURE_KEY = "_jira_failure_info"


class JiraReporterPlugin:
    """Collects Jira context, then creates/updates a Bug for each failed test."""

    def __init__(self) -> None:
        self._client: _JiraClient | None = None

    def _get_client(self) -> _JiraClient | None:
        if self._client is not None:
            return self._client
        required = ("JIRA_URL", "JIRA_USERNAME", "JIRA_API_TOKEN")
        if not all(os.environ.get(k) for k in required):
            return None
        try:
            self._client = _JiraClient()
        except Exception as exc:
            print(f"\n[jira-reporter] Failed to init client: {exc}")
        return self._client

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: pytest.Item, call: pytest.CallInfo):
        outcome = yield
        rep = outcome.get_result()

        # Phase 1 (call): store failure info for use in teardown phase
        if rep.when == "call" and rep.failed:
            longrepr = str(rep.longrepr) if rep.longrepr else "No traceback available."
            setattr(item, _FAILURE_KEY, {"nodeid": item.nodeid, "longrepr": longrepr})

        # Phase 2 (teardown): screenshot is on disk; collect context then act
        elif rep.when == "teardown":
            failure = getattr(item, _FAILURE_KEY, None)
            if failure is None:
                return

            client = self._get_client()
            if client is None:
                return

            nodeid = failure["nodeid"]
            longrepr = failure["longrepr"]
            screenshot = _screenshot_path_for(nodeid)

            label_hash = hashlib.sha1(nodeid.encode()).hexdigest()[:12]
            dedup_label = f"pytest-auto:{label_hash}"

            # ── Collect Jira context (dedup + similar + comments) ──────────────
            ctx: dict = {}
            try:
                collector = JiraContextCollector(
                    base_url=client.base_url,
                    auth=(os.environ["JIRA_USERNAME"], os.environ["JIRA_API_TOKEN"]),
                    project_key=client.project_key,
                )
                ctx = collector.collect(nodeid, longrepr, dedup_label)
                collector.close()
            except Exception as exc:
                print(f"\n[jira-reporter] Context collection failed: {exc}")

            # Attach context JSON to Allure for LLM inspection
            if ctx:
                try:
                    allure.attach(
                        json.dumps(ctx, indent=2, ensure_ascii=False),
                        name="Jira context (LLM input)",
                        attachment_type=allure.attachment_type.JSON,
                    )
                except Exception:
                    pass

            # ── Act on the context ─────────────────────────────────────────────
            fingerprint_match = ctx.get("fingerprint_match")
            try:
                if fingerprint_match:
                    issue_key = fingerprint_match["key"]
                    client.add_comment(
                        issue_key,
                        f"Test failed again.\n\nTest: {nodeid}\n"
                        f"Recommendation: {ctx.get('recommendation', '')}",
                    )
                    print(f"\n[jira-reporter] Updated {issue_key} ({nodeid})")
                else:
                    summary = f"[TEST FAIL] {nodeid}"
                    description = _build_description(nodeid, longrepr, has_screenshot=bool(screenshot))
                    labels = ["pytest-auto", "automated-test-failure", dedup_label]
                    issue_key = client.create_bug(summary, description, labels)
                    similar = ctx.get("similar_bugs", [])
                    print(
                        f"\n[jira-reporter] Created {issue_key} → "
                        f"{client.base_url}/browse/{issue_key}"
                        + (f"  (similar: {', '.join(b['key'] for b in similar)})" if similar else "")
                    )

                if screenshot:
                    client.attach_screenshot(issue_key, screenshot)
                    print(f"[jira-reporter] Attached screenshot to {issue_key}")

            except Exception as exc:
                print(f"\n[jira-reporter] ERROR for {nodeid}: {exc}")

    def pytest_sessionfinish(self, session, exitstatus) -> None:
        if self._client:
            self._client.close()


# ── Auto-registration ─────────────────────────────────────────────────────────

def pytest_configure(config: pytest.Config) -> None:
    if os.environ.get("JIRA_REPORT_FAILURES", "").lower() in ("1", "true", "yes"):
        config.pluginmanager.register(JiraReporterPlugin(), "jira_reporter")
