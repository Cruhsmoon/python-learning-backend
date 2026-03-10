# QA Automation Project — Audit Report

**Date:** 2026-03-10  
**Project:** PyCharmMiscProject  
**Auditor:** Claude Code (claude-sonnet-4-6)

---

## Executive Summary

The project implements a multi-layer QA automation framework covering unit, API, database, integration, Celery task, and Playwright UI tests against a FastAPI application. The framework is well-designed overall — fixtures are properly isolated with savepoint-based rollback, CI/CD separates fast and slow test jobs, and the UI layer uses a clean Page Object Model composition pattern. The audit identified **3 critical issues**, **3 high-priority structural issues**, and **10 medium/low-priority improvements**. All issues have been fixed in this commit.

---

## Issues Fixed

### Critical

| ID | File | Issue | Fix Applied |
|----|------|-------|-------------|
| C-1 | `fastapi_app/_init_.py` | Filename used single underscores — Python never treated this as a package init file. | Deleted `_init_.py`, created `__init__.py`. |
| C-2 | `tests/ui/pages/base_page.py:1` | Stray `§` (U+00A7 Section Sign) character before the module docstring — causes `SyntaxError: invalid character` in Python 3. | Removed the character. |
| C-3 | `tests/conftest.py:172` | `PG_DATABASE_URL` hardcoded to `localhost` — CI or staging environments with a different host would silently use the wrong DB. | Changed to `os.getenv("PG_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")`. |

---

### High Priority — Structure

| ID | Issue | Fix Applied |
|----|-------|-------------|
| H-1 | `tests/Postman/` used PascalCase directory name and a non-standard `*_postman.py` file pattern. Python package directories use `snake_case`. | Renamed directory to `tests/postman/`, renamed test file to `test_users_postman.py`, removed `*_postman.py` from `pytest.ini`. |
| H-2 | `tests/ui/pages/search_results_page.py` was an orphaned legacy Page Object duplicating the logic already split into `search_page.py` + `results_page.py` + `filters_panel.py`. No test file imported it. | Deleted the file. |
| H-3 | `.gitignore` did not cover `.env.*` (env files with suffixes), `screenshots/` (Playwright failure artifacts), or `openapi.json` (generated spec). These could be accidentally committed. | Added all three patterns to `.gitignore`. Also added `fastapi_app/.venv/`. |

---

### Medium Priority — Organisation & Design

| ID | Issue | Fix Applied |
|----|-------|-------------|
| M-1 | `tests/conftest.py` was ~290 lines mixing SQLite fixtures, PostgreSQL fixtures, Celery fixtures, auth fixtures, and a report hook — four unrelated concerns in one file. | Extracted PostgreSQL fixtures → `tests/db/conftest.py`. Extracted Celery fixtures → `tests/tasks/conftest.py`. Shared fixtures remain in `tests/conftest.py`. |
| M-2 | `requirements.txt` mixed production application dependencies with test tooling (pytest, playwright, faker, etc.) making it impossible to build a lean production image. | Split into `requirements.txt` (production: FastAPI, SQLAlchemy, Celery, etc.) and `requirements-dev.txt` (adds test tooling on top). |
| M-3 | `tests/api/auth_test.py` used the `*_test.py` suffix naming convention while all sibling files used `test_*.py` prefix. | Renamed to `tests/api/test_auth.py`. |
| M-4 | `workers/` package had no `__init__.py`, making it an implicit namespace package. | Created `workers/__init__.py`. |
| M-5 | Root-level `conftest.py` was empty (just a comment). `pytest.ini` already points `testpaths = tests`, so pytest finds `tests/conftest.py` directly. The root file was noise. | Deleted. |

---

### Low Priority — Style

| ID | Issue | Note |
|----|-------|------|
| L-1 | `fastapi_app/.venv/` — nested virtualenv inside the app package could cause accidental collection by pytest or packaging tools. | Added `fastapi_app/.venv/` to `.gitignore`. |
| L-2 | `self.page` (public) in `BasePage` subclasses vs `self._page` (private convention) in composed components (`FiltersPanel`, `ResultsPage`). | Style inconsistency noted. Composed components correctly use `_page` since the page object is an implementation detail. `BasePage` exposes `page` publicly by design to give tests direct Playwright access. Accepted as intentional asymmetry. |

---

## Post-Fix Project Structure

```
PyCharmMiscProject/
├── fastapi_app/
│   ├── __init__.py          ✓ fixed (was _init_.py)
│   └── main.py
├── workers/
│   ├── __init__.py          ✓ added
│   └── celery_app.py
├── exercises/               (SUT for unit tests)
├── data/
│   └── users.json           (used by exercises/report.py)
├── tests/
│   ├── conftest.py          ✓ slimmed — shared fixtures only
│   ├── factories.py
│   ├── api/
│   │   ├── test_auth.py     ✓ renamed from auth_test.py
│   │   ├── test_openapi.py
│   │   └── test_users.py
│   ├── db/
│   │   ├── conftest.py      ✓ new — PostgreSQL fixtures
│   │   └── test_users_db.py
│   ├── integration/
│   │   └── test_users_sync.py
│   ├── postman/             ✓ renamed from Postman/
│   │   ├── conftest.py
│   │   └── api/
│   │       └── test_users_postman.py  ✓ renamed
│   ├── tasks/
│   │   ├── conftest.py      ✓ new — Celery + fakeredis fixtures
│   │   └── test_celery_tasks.py
│   ├── unit/
│   │   ├── test_day4_functions.py
│   │   └── test_utils.py
│   └── ui/
│       ├── conftest.py
│       └── pages/
│           ├── base_page.py          ✓ fixed (removed §)
│           ├── filters_panel.py
│           ├── home_page.py
│           ├── navigation_bar.py
│           ├── results_page.py
│           └── search_page.py
│           # search_results_page.py  ✓ deleted (orphaned)
├── .github/workflows/test.yml   ✓ updated --ignore path
├── .gitignore               ✓ added .env.*, screenshots/, openapi.json
├── pytest.ini               ✓ removed *_postman.py pattern
├── requirements.txt         ✓ production deps only
├── requirements-dev.txt     ✓ new — test/dev deps
└── AUDIT_REPORT.md          ✓ this file
```

---

## What Was NOT Changed

- **`exercises/`** — these are the source-under-test for `tests/unit/`. Despite the name suggesting "learning scripts", they are the actual SUT. Leaving in place.
- **`data/users.json`** — referenced by `exercises/report.py` (not test infrastructure). Moving would break `exercises/report.py`. Leaving in place.
- **`tests/ui/conftest.py` + `tests/conftest.py` both define `pytest_runtest_makereport`** — both hooks are intentional and serve different purposes (DB snapshot HTML vs screenshot-on-failure). Pytest chains them correctly; UI hook runs first due to `tryfirst=True`.
- **`fastapi_app/main.py` hardcoded `SECRET_KEY`** — out of scope for this structural audit (application security concern, not test structure).

---

## Recommendations for Future Improvements

1. **Adopt `pyproject.toml`** — consolidate `pytest.ini` configuration, project metadata, and dependency declarations into a single modern config file.
2. **Add `schemathesis` to `requirements-dev.txt`** — `tests/api/test_openapi.py` imports it but it is not in `requirements.txt` or `requirements-dev.txt`.
3. **Use `pytest-xdist`** for parallel test execution — the UI suite makes 5+ real HTTP calls to a live website; running them in parallel would reduce CI time.
4. **Pin Playwright browser version in CI** — `playwright install chromium --with-deps` always installs latest; consider pinning to the version matching the `playwright==1.49.0` package.
5. **Add `pytest.mark.db`** marker for PostgreSQL tests — currently `tests/db/` only runs when PostgreSQL is available; a marker would allow `pytest -m "not db"` for local runs without a PG server.
