"""
Jira context collector — tests/plugins/jira_context.py
=======================================================
Collects structured Jira context before a new Bug is filed.
The returned JSON is compact enough to drop directly into an LLM prompt.

API call order
--------------
  1. POST /rest/api/3/search/jql   — fingerprint search (exact dedup label)
  2. POST /rest/api/3/search/jql   — keyword search by test file / module
  3. POST /rest/api/3/search/jql   — keyword search by exception type (optional)
  4. POST /rest/api/3/search/jql   — keyword search by HTTP endpoint (optional)
  5. GET  /rest/api/3/issue/{key}/comment  — recent comments (≤3 per matched issue)

Usage
-----
    from tests.plugins.jira_context import JiraContextCollector

    collector = JiraContextCollector(
        base_url="https://your-site.atlassian.net",
        auth=("email@example.com", "api-token"),
        project_key="KAN",
    )
    ctx = collector.collect(
        nodeid="tests/api/test_users.py::test_create_user",
        longrepr="AssertionError: expected 201, got 422\\n...",
        dedup_label="pytest-auto:abc123",
    )
    # ctx is a dict ready for json.dumps() and LLM input
    collector.close()
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx


# ── ADF → plain text ──────────────────────────────────────────────────────────

def _adf_to_text(node: Any, depth: int = 0) -> str:
    """
    Recursively flatten an Atlassian Document Format (ADF) node to plain text.
    Handles doc, paragraph, heading, codeBlock, bulletList, text, etc.
    """
    if not isinstance(node, dict):
        return ""

    node_type = node.get("type", "")
    text_parts: list[str] = []

    if node_type == "text":
        return node.get("text", "")

    for child in node.get("content", []):
        part = _adf_to_text(child, depth + 1)
        if part:
            text_parts.append(part)

    joined = " ".join(text_parts)

    if node_type in ("heading", "paragraph", "codeBlock"):
        return f"{joined}\n"
    if node_type in ("listItem", "bulletList", "orderedList"):
        return f"• {joined}"
    return joined


# ── Error type extractor ──────────────────────────────────────────────────────

def _extract_error_type(longrepr: str) -> str | None:
    """
    Parse the pytest failure repr to find the exception class name.
    Tries last-line first (most specific), then scans backwards.

    Examples matched:
        AssertionError: …
        httpx.HTTPStatusError: …
        playwright._impl._errors.TimeoutError: …
        sqlalchemy.exc.IntegrityError: …
    """
    pattern = re.compile(
        r"^(?:[\w.]+\.)?([A-Z][A-Za-z0-9]*(?:Error|Exception|Failure|Warning))\s*:",
        re.MULTILINE,
    )
    matches = pattern.findall(longrepr)
    return matches[-1] if matches else None


# ── HTTP endpoint extractor ───────────────────────────────────────────────────

def _extract_endpoint(longrepr: str, nodeid: str) -> str | None:
    """
    Try to find an HTTP endpoint in the failure repr or the test node ID.

    Strategies (in order):
      1. Literal URL path in longrepr:  GET /users/me, POST /auth/login
      2. Infer from test name:  test_create_user → /users
    """
    # Strategy 1: explicit method + path in repr
    m = re.search(
        r"(?:GET|POST|PUT|PATCH|DELETE)\s+(/[a-zA-Z0-9_/-]+)",
        longrepr,
        re.IGNORECASE,
    )
    if m:
        return m.group(1)

    # Strategy 2: infer from test node ID
    test_name = nodeid.split("::")[-1].lower()
    # e.g. test_create_user → /users, test_get_me → /me
    _inference_map = {
        "login": "/auth/login",
        "auth": "/auth/login",
        "user": "/users",
        "users": "/users",
        "me": "/users/me",
        "admin": "/admin/users",
        "health": "/health",
    }
    for keyword, path in _inference_map.items():
        if keyword in test_name:
            return path

    return None


# ── Jira context collector ────────────────────────────────────────────────────

class JiraContextCollector:
    """
    Queries Jira Cloud REST API to build context for LLM-based duplicate detection.

    All heavy lifting is done in `collect()`. Each `_search_*` and
    `_get_comments` method maps 1-to-1 to a single API call.
    """

    def __init__(
        self,
        base_url: str,
        auth: tuple[str, str],
        project_key: str = "KAN",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.project_key = project_key
        self._client = httpx.Client(
            auth=auth,
            timeout=15,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    # ── Low-level helpers ──────────────────────────────────────────────────────

    def _post_search(
        self,
        jql: str,
        fields: list[str],
        max_results: int = 5,
    ) -> list[dict]:
        """
        POST /rest/api/3/search/jql
        Returns raw Jira issue dicts.
        """
        resp = self._client.post(
            f"{self.base_url}/rest/api/3/search/jql",
            content=json.dumps(
                {"jql": jql, "maxResults": max_results, "fields": fields}
            ),
        )
        resp.raise_for_status()
        return resp.json().get("issues", [])

    def _get_comments(self, issue_key: str, max_results: int = 3) -> list[dict]:
        """
        GET /rest/api/3/issue/{issueKey}/comment?orderBy=-created&maxResults=N
        Returns simplified comment list (author, created, body as plain text).
        """
        resp = self._client.get(
            f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
            params={"orderBy": "-created", "maxResults": max_results},
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "author": c["author"]["displayName"],
                "created": c["created"][:19],   # trim timezone noise
                "body": _adf_to_text(c.get("body", {})).strip()[:500],
            }
            for c in data.get("comments", [])
        ]

    def _simplify(self, issue: dict, match_reason: str = "") -> dict:
        """Flatten a raw Jira issue to a compact dict for LLM consumption."""
        f = issue.get("fields", {})
        return {
            "key": issue["key"],
            "summary": f.get("summary", ""),
            "status": f.get("status", {}).get("name", ""),
            "created": (f.get("created") or "")[:10],
            "updated": (f.get("updated") or "")[:10],
            "url": f"{self.base_url}/browse/{issue['key']}",
            **({"match_reason": match_reason} if match_reason else {}),
        }

    # ── Named search steps ─────────────────────────────────────────────────────

    def search_fingerprint(self, dedup_label: str) -> dict | None:
        """
        Step 1 — Exact duplicate check via the stable fingerprint label.

        JQL:
            project = "KAN"
            AND issuetype = Bug
            AND labels = "pytest-auto:<hash>"
            AND statusCategory != "Done"

        Returns the first matched issue, or None.
        """
        jql = (
            f'project = "{self.project_key}"'
            f' AND issuetype = Bug'
            f' AND labels = "{dedup_label}"'
            f' AND statusCategory != "Done"'
        )
        issues = self._post_search(
            jql,
            fields=["summary", "status", "created", "updated", "labels"],
            max_results=1,
        )
        return self._simplify(issues[0], "exact_fingerprint") if issues else None

    def search_by_file(self, test_module: str) -> list[dict]:
        """
        Step 2a — Similar bugs mentioning the same test file / module name.

        JQL:
            project = "KAN"
            AND issuetype = Bug
            AND statusCategory != "Done"
            AND summary ~ "test_smoke"
            ORDER BY created DESC
        """
        jql = (
            f'project = "{self.project_key}"'
            f' AND issuetype = Bug'
            f' AND statusCategory != "Done"'
            f' AND summary ~ "{test_module}"'
            f' ORDER BY created DESC'
        )
        issues = self._post_search(
            jql,
            fields=["summary", "status", "created", "updated"],
            max_results=5,
        )
        return [self._simplify(i, "file_match") for i in issues]

    def search_by_exception(self, error_type: str) -> list[dict]:
        """
        Step 2b — Similar bugs with the same exception class in summary or text.

        JQL:
            project = "KAN"
            AND issuetype = Bug
            AND statusCategory != "Done"
            AND (summary ~ "AssertionError" OR text ~ "AssertionError")
            ORDER BY created DESC
        """
        jql = (
            f'project = "{self.project_key}"'
            f' AND issuetype = Bug'
            f' AND statusCategory != "Done"'
            f' AND (summary ~ "{error_type}" OR text ~ "{error_type}")'
            f' ORDER BY created DESC'
        )
        issues = self._post_search(
            jql,
            fields=["summary", "status", "created", "updated"],
            max_results=5,
        )
        return [self._simplify(i, "exception_match") for i in issues]

    def search_by_endpoint(self, endpoint: str) -> list[dict]:
        """
        Step 2c — Similar bugs referencing the same HTTP endpoint.

        JQL:
            project = "KAN"
            AND issuetype = Bug
            AND statusCategory != "Done"
            AND (summary ~ "/users" OR text ~ "/users")
            ORDER BY created DESC
        """
        # Strip leading slash for JQL text search compatibility
        token = endpoint.lstrip("/")
        jql = (
            f'project = "{self.project_key}"'
            f' AND issuetype = Bug'
            f' AND statusCategory != "Done"'
            f' AND (summary ~ "{token}" OR text ~ "{token}")'
            f' ORDER BY created DESC'
        )
        issues = self._post_search(
            jql,
            fields=["summary", "status", "created", "updated"],
            max_results=5,
        )
        return [self._simplify(i, "endpoint_match") for i in issues]

    def fetch_recent_comments(
        self,
        issue_keys: list[str],
        max_comments: int = 3,
    ) -> dict[str, list[dict]]:
        """
        Step 3 — Fetch recent comments for matched issues (≤3 issues).

        GET /rest/api/3/issue/{key}/comment  (one call per issue)
        """
        return {
            key: self._get_comments(key, max_results=max_comments)
            for key in issue_keys[:3]
        }

    # ── Main entry point ───────────────────────────────────────────────────────

    def collect(
        self,
        nodeid: str,
        longrepr: str,
        dedup_label: str,
    ) -> dict:
        """
        Orchestrate all Jira API calls and return a compact JSON context.

        Call order
        ----------
        1. search_fingerprint      → POST /rest/api/3/search/jql  (1 call)
        2. search_by_file          → POST /rest/api/3/search/jql  (1 call)
        3. search_by_exception     → POST /rest/api/3/search/jql  (1 call, if error found)
        4. search_by_endpoint      → POST /rest/api/3/search/jql  (1 call, if endpoint found)
        5. fetch_recent_comments   → GET  /rest/api/3/issue/{key}/comment  (≤3 calls)

        Total: 3–7 API calls per failed test.

        Parameters
        ----------
        nodeid      : pytest node ID  (tests/api/test_users.py::test_create_user)
        longrepr    : full pytest failure repr (traceback + assertion)
        dedup_label : fingerprint label (pytest-auto:<sha1_hash>)

        Returns
        -------
        Compact dict ready for json.dumps() and LLM input.
        """
        # ── Extract signal tokens ──────────────────────────────────────────────
        test_file = Path(nodeid.split("::")[0]).name          # test_users.py
        test_module = test_file.removesuffix(".py")           # test_users
        error_type = _extract_error_type(longrepr)            # AssertionError | None
        endpoint = _extract_endpoint(longrepr, nodeid)        # /users | None

        # ── Step 1: Exact fingerprint check ───────────────────────────────────
        fingerprint_match = self.search_fingerprint(dedup_label)

        # ── Steps 2a-2c: Keyword similarity (skip if exact match found) ───────
        similar_bugs: dict[str, dict] = {}

        if not fingerprint_match:
            for issue in self.search_by_file(test_module):
                similar_bugs.setdefault(issue["key"], issue)

            if error_type:
                for issue in self.search_by_exception(error_type):
                    if issue["key"] not in similar_bugs:
                        similar_bugs[issue["key"]] = issue

            if endpoint:
                for issue in self.search_by_endpoint(endpoint):
                    if issue["key"] not in similar_bugs:
                        similar_bugs[issue["key"]] = issue

        similar_list = list(similar_bugs.values())[:5]

        # ── Step 3: Recent comments ────────────────────────────────────────────
        comment_keys = (
            [fingerprint_match["key"]] if fingerprint_match
            else [b["key"] for b in similar_list]
        )
        recent_comments = self.fetch_recent_comments(comment_keys)

        # ── Recommendation ─────────────────────────────────────────────────────
        if fingerprint_match:
            recommendation = "DUPLICATE — add comment + screenshot to existing issue"
        elif similar_list:
            recommendation = "SIMILAR — review matches before filing a new issue"
        else:
            recommendation = "NEW — no existing issues found, safe to create"

        # ── Compact JSON context ───────────────────────────────────────────────
        return {
            "test_context": {
                "nodeid": nodeid,
                "file": test_file,
                "module": test_module,
                "error_type": error_type,
                "endpoint": endpoint,
                "dedup_label": dedup_label,
            },
            "jira_project": self.project_key,
            "fingerprint_match": fingerprint_match,
            "similar_bugs": similar_list,
            "recent_comments": recent_comments,
            "recommendation": recommendation,
        }

    def close(self) -> None:
        self._client.close()
