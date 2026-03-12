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


def _adf_bullet_list(items: list[str]) -> dict:
    """Build an ADF bulletList from a list of plain-text strings."""
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [_adf_paragraph(item)],
            }
            for item in items
        ],
    }


def _adf_ordered_list(items: list[str]) -> dict:
    """Build an ADF orderedList from a list of plain-text strings."""
    return {
        "type": "orderedList",
        "content": [
            {
                "type": "listItem",
                "content": [_adf_paragraph(item)],
            }
            for item in items
        ],
    }


def _generate_action_plan(
    nodeid: str,
    longrepr: str,
    ctx: dict,
    base_url: str,
) -> list[str]:
    """
    Produce a concrete, context-aware action plan for the assigned developer.

    Rules:
      - Always starts with reproduce + recent-commits steps.
      - Adds error-type-specific investigation steps.
      - If similar bugs exist, references them explicitly.
      - If the test is a UI test, adds browser-inspection steps.
      - Closes with fix-or-update step.
    """
    from pathlib import Path as _Path
    from tests.plugins.jira_context import _extract_error_type

    test_file = _Path(nodeid.split("::")[0]).name
    test_name = nodeid.split("::")[-1]
    error_type = _extract_error_type(longrepr) or "unknown error"
    is_ui = "ui" in nodeid or "playwright" in longrepr.lower()
    endpoint = ctx.get("test_context", {}).get("endpoint")
    similar = ctx.get("similar_bugs", [])

    steps: list[str] = []

    # Step 1 — reproduce
    steps.append(
        f"Reproduce the failure locally:\n"
        f"  JIRA_REPORT_FAILURES=1 pytest \"{nodeid}\" -v"
        + (" -m ui" if is_ui else "")
    )

    # Step 2 — recent commits
    steps.append(
        f"Review recent commits that touched {test_file} or related source files:\n"
        f"  git log --oneline --since='7 days ago' -- tests/ui/ src/"
    )

    # Step 3 — error-specific investigation
    if "missing links" in longrepr.lower() or "has_link_to" in longrepr.lower():
        # Extract the missing links from the error message
        import re as _re
        link_match = _re.search(r"missing links to:\s*(\[.*?\])", longrepr)
        missing = link_match.group(1) if link_match else "the expected hrefs"
        steps.append(
            f"Open {base_url.replace(ctx.get('jira_project',''), '').rstrip('/')} "
            f"in a browser and verify the navigation bar — check whether "
            f"{missing} appear as <a> elements in the DOM."
        )
        steps.append(
            "Search the frontend codebase for the missing route:\n"
            "  grep -r 'careers\\|/careers' src/ --include='*.js' --include='*.ts'"
        )
    elif error_type == "AssertionError":
        steps.append(
            "Inspect the assertion that failed — compare the actual value printed "
            "in the traceback against the expected value hard-coded in the test. "
            "Determine whether the application or the test expectation has drifted."
        )
    elif "TimeoutError" in error_type or "timeout" in longrepr.lower():
        steps.append(
            "The element did not appear within the timeout. "
            "Check: (a) selector is still correct, (b) page is not behind a loader/spinner, "
            "(c) network latency did not increase. Increase timeout temporarily to confirm."
        )
    elif error_type != "unknown error":
        steps.append(
            f"Investigate the root cause of {error_type}. "
            "Read the full traceback attached to this issue and identify the "
            "first frame in application code (not framework code)."
        )

    # Step 4 — UI-specific
    if is_ui:
        steps.append(
            "Open the full-page screenshot attached to this issue. "
            "Visually confirm the page state at the moment of failure — "
            "check for unexpected modals, cookie banners, or layout shifts."
        )

    # Step 5 — endpoint-specific
    if endpoint:
        steps.append(
            f"If the failure is related to API endpoint {endpoint}, "
            "verify the endpoint contract with:\n"
            f"  pytest tests/api/ -k \"{endpoint.strip('/').replace('/', '_')}\" -v"
        )

    # Step 6 — similar issues
    if similar:
        refs = ", ".join(
            f"{b['key']} ({b.get('match_reason', 'similar')})" for b in similar[:3]
        )
        steps.append(
            f"Review similar open issues for context before starting a fix: {refs}. "
            "Their comments may contain a root-cause analysis or a partial fix."
        )

    # Step 7 — resolution
    steps.append(
        "Once the root cause is identified:\n"
        "  (a) Fix the application code and verify the test passes, OR\n"
        "  (b) If the test expectation is wrong, update it with a clear comment "
        "explaining why, and get a second reviewer to approve."
    )

    return steps


def _build_description(
    nodeid: str,
    longrepr: str,
    has_screenshot: bool,
    ctx: dict,
    base_url: str,
) -> dict:
    from pathlib import Path as _Path
    from tests.plugins.jira_context import _extract_error_type

    test_file = _Path(nodeid.split("::")[0]).name
    error_type = _extract_error_type(longrepr) or "—"
    endpoint = ctx.get("test_context", {}).get("endpoint", "—")
    similar = ctx.get("similar_bugs", [])
    recommendation = ctx.get("recommendation", "")
    truncated = textwrap.shorten(longrepr, width=8_000, placeholder="\n…(truncated)")
    action_steps = _generate_action_plan(nodeid, longrepr, ctx, base_url)

    blocks = [
        # ── Summary ──────────────────────────────────────────────────────────
        _adf_heading("Bug Summary", level=2),
        _adf_bullet_list([
            f"Test file:      {test_file}",
            f"Full node ID:   {nodeid}",
            f"Error type:     {error_type}",
            f"Endpoint:       {endpoint}",
            f"Duplicate check: {recommendation}",
        ]),

        # ── Failure traceback ─────────────────────────────────────────────────
        _adf_heading("Failure Traceback", level=2),
        _adf_code_block(truncated, language="text"),

        # ── How to reproduce ──────────────────────────────────────────────────
        _adf_heading("How to Reproduce", level=2),
        _adf_code_block(
            f"# From the project root:\n"
            f"JIRA_REPORT_FAILURES=1 pytest \"{nodeid}\" -v"
            + (" -m ui --tb=short" if "ui" in nodeid else " --tb=short"),
            language="bash",
        ),
    ]

    # ── Screenshot notice ─────────────────────────────────────────────────────
    if has_screenshot:
        blocks += [
            _adf_heading("Screenshot", level=2),
            _adf_paragraph(
                "A full-page Playwright screenshot captured at the moment of failure "
                "is attached to this issue. Open it to see the exact browser state."
            ),
        ]

    # ── Similar issues ────────────────────────────────────────────────────────
    if similar:
        blocks.append(_adf_heading("Related Issues", level=2))
        blocks.append(
            _adf_bullet_list([
                f"{b['key']} [{b.get('match_reason', 'similar')}] — {b['summary']} ({b['status']})"
                for b in similar[:5]
            ])
        )

    # ── Action plan ───────────────────────────────────────────────────────────
    blocks.append(_adf_heading("Action Plan", level=2))
    blocks.append(_adf_ordered_list(action_steps))

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
                    description = _build_description(
                        nodeid, longrepr,
                        has_screenshot=bool(screenshot),
                        ctx=ctx,
                        base_url=client.base_url,
                    )
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
