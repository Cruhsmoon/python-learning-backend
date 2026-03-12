"""
Jira bug reporter — tests/plugins/jira_reporter.py
====================================================
Automatically creates a Jira Bug when a test fails.

Activation
----------
Set the environment variable before running pytest:

    JIRA_REPORT_FAILURES=1 pytest ...

Or add it to your shell profile / CI environment.

Configuration (via .env.jira or environment variables)
-------------------------------------------------------
    JIRA_URL           – https://<your-site>.atlassian.net
    JIRA_USERNAME      – your Atlassian account email
    JIRA_API_TOKEN     – Atlassian API token
    JIRA_PROJECT_KEY   – Project key to create bugs in (default: KAN)
    JIRA_BUG_TYPE_ID   – Issue type ID for Bug (default: 10010)

Deduplication
-------------
Before creating a new issue the reporter searches for open bugs with the
label  pytest-auto:<test_nodeid_hash>. If one already exists the run URL
is added as a comment instead of opening a duplicate.
"""

from __future__ import annotations

import hashlib
import json
import os
import textwrap
from pathlib import Path
from typing import Any

import httpx
import pytest


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


# ── Jira client ───────────────────────────────────────────────────────────────

class _JiraClient:
    def __init__(self) -> None:
        self.base_url = os.environ["JIRA_URL"].rstrip("/")
        self.auth = (
            os.environ["JIRA_USERNAME"],
            os.environ["JIRA_API_TOKEN"],
        )
        self.project_key = os.environ.get("JIRA_PROJECT_KEY", "KAN")
        self.bug_type_id = os.environ.get("JIRA_BUG_TYPE_ID", "10010")
        self._client = httpx.Client(auth=self.auth, timeout=15)

    def _api(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = f"{self.base_url}/rest/api/3{path}"
        resp = self._client.request(
            method, url,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def find_open_bug(self, label: str) -> str | None:
        """Return issue key if an open bug with this label already exists."""
        jql = (
            f'project = "{self.project_key}" '
            f'AND issuetype = Bug '
            f'AND labels = "{label}" '
            f'AND statusCategory != "Done"'
        )
        payload = {"jql": jql, "maxResults": 1, "fields": ["key", "summary"]}
        data = self._api("POST", "/search/jql", content=json.dumps(payload))
        issues = data.get("issues", [])
        return issues[0]["key"] if issues else None

    def create_bug(self, summary: str, description_adf: dict, labels: list[str]) -> str:
        """Create a Bug and return its issue key (e.g. KAN-42)."""
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "issuetype": {"id": self.bug_type_id},
                "summary": summary,
                "description": description_adf,
                "labels": labels,
            }
        }
        data = self._api("POST", "/issue", content=json.dumps(payload))
        return data["key"]

    def add_comment(self, issue_key: str, text: str) -> None:
        """Add a plain-text comment to an existing issue."""
        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": text}],
                    }
                ],
            }
        }
        self._api("POST", f"/issue/{issue_key}/comment", content=json.dumps(body))

    def close(self) -> None:
        self._client.close()


# ── ADF (Atlassian Document Format) helpers ───────────────────────────────────

def _adf_doc(*blocks) -> dict:
    return {"type": "doc", "version": 1, "content": list(blocks)}


def _adf_heading(text: str, level: int = 2) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [{"type": "text", "text": text}],
    }


def _adf_paragraph(text: str) -> dict:
    return {
        "type": "paragraph",
        "content": [{"type": "text", "text": text}],
    }


def _adf_code_block(code: str, language: str = "text") -> dict:
    return {
        "type": "codeBlock",
        "attrs": {"language": language},
        "content": [{"type": "text", "text": code}],
    }


def _build_description(nodeid: str, longrepr: str) -> dict:
    truncated = textwrap.shorten(longrepr, width=10_000, placeholder="\n…(truncated)")
    return _adf_doc(
        _adf_heading("Test Information", level=2),
        _adf_paragraph(f"Test: {nodeid}"),
        _adf_heading("Failure Details", level=2),
        _adf_code_block(truncated, language="text"),
        _adf_heading("How to Reproduce", level=2),
        _adf_paragraph(f"pytest {nodeid}"),
    )


# ── Pytest plugin ─────────────────────────────────────────────────────────────

class JiraReporterPlugin:
    """Pytest plugin: creates a Jira Bug for each failed test."""

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
            print(f"\n[jira-reporter] Failed to initialise Jira client: {exc}")
        return self._client

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: pytest.Item, call: pytest.CallInfo):
        outcome = yield
        rep = outcome.get_result()

        if rep.when != "call" or not rep.failed:
            return

        client = self._get_client()
        if client is None:
            return

        longrepr = str(rep.longrepr) if rep.longrepr else "No traceback available."
        nodeid = item.nodeid

        # Stable label for deduplication
        label_hash = hashlib.sha1(nodeid.encode()).hexdigest()[:12]
        dedup_label = f"pytest-auto:{label_hash}"

        summary = f"[TEST FAIL] {nodeid}"
        description = _build_description(nodeid, longrepr)
        labels = ["pytest-auto", "automated-test-failure", dedup_label]

        try:
            existing = client.find_open_bug(dedup_label)
            if existing:
                client.add_comment(
                    existing,
                    f"Test failed again in a new run.\n\nTest: {nodeid}",
                )
                print(f"\n[jira-reporter] Updated existing bug {existing} ({nodeid})")
            else:
                key = client.create_bug(summary, description, labels)
                print(f"\n[jira-reporter] Created Jira bug {key} → {client.base_url}/browse/{key}")
        except Exception as exc:
            print(f"\n[jira-reporter] ERROR creating Jira issue for {nodeid}: {exc}")

    def pytest_sessionfinish(self, session, exitstatus) -> None:
        if self._client:
            self._client.close()


# ── Auto-registration ─────────────────────────────────────────────────────────

def pytest_configure(config: pytest.Config) -> None:
    if os.environ.get("JIRA_REPORT_FAILURES", "").lower() in ("1", "true", "yes"):
        config.pluginmanager.register(JiraReporterPlugin(), "jira_reporter")
