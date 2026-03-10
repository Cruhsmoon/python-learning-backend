![CI](https://github.com/Crushmoon/python-learning-backend/actions/workflows/test.yml/badge.svg)

# Python Learning Backend

This repository contains exercises and backend experiments:

- JSON parsing and reporting script
- FastAPI basics
- PostgreSQL via Docker
- Redis setup
- Celery experiments
- Gemini CLI refactoring

## How to run

```bash
python scripts/report.py
```

---

## Testing

### Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run tests

```bash
# All tests
pytest

# With coverage (branch + HTML report)
pytest --cov=src --cov-branch --cov-fail-under=80

# Specific suites
pytest tests/unit/           # unit tests only
pytest tests/integration/    # sync integration tests
pytest tests/api/            # async API tests
```

After a coverage run, open `htmlcov/index.html` in a browser to view the
line-by-line HTML report.

### Test structure

```
tests/
├── conftest.py                      # shared fixtures + HTML report hook
├── fixtures/
│   └── factories.py                 # Faker-based data generators
├── api/
│   └── test_users.py                # 22 async integration tests (HTTPX + ASGITransport)
├── integration/
│   └── test_users_sync.py           # 22 sync integration tests (Starlette TestClient)
├── postman/
│   └── test_users_postman.py        # postman-style API tests
└── unit/
    ├── test_utils.py                # 10 baseline unit tests
    └── test_functions.py            # 42 edge-case unit tests
```

**Total: 96 tests — all green locally and in CI.**

### Architectural decisions

| Decision | Reason |
|---|---|
| **SQLite in-memory + StaticPool** | Tests run without a live PostgreSQL server. StaticPool ensures all connections share one DBAPI connection, which is required for the savepoint-based rollback strategy. |
| **Transaction rollback isolation** | Each test wraps its DB work in a real `BEGIN` → `SAVEPOINT` → `ROLLBACK` cycle. No data persists between tests and no `DROP`/`CREATE` is needed per test, keeping the suite fast. |
| **`patch_production_engine` (autouse, session)** | Replaces `src.api.main.engine` with the SQLite test engine once per session so that any code path that reads the module-level `engine` (including the lifespan handler) uses SQLite instead of PostgreSQL. |
| **`sync_client` without context manager** | Using `with TestClient(app)` runs the ASGI lifespan, which calls `create_all(bind=engine)`. With StaticPool that issues an internal `COMMIT` on the shared connection, silently ending the outer `BEGIN` and breaking rollback teardown. Tables are already created by the session-scoped `test_engine` fixture, so skipping the lifespan is safe. |
| **`lifespan` handler instead of module-level `create_all`** | Moving `Base.metadata.create_all` from module scope into the FastAPI lifespan handler means importing `src.api.main` no longer requires a live database. The handler reads the module-level `engine` at call time, so the test patch takes effect before the first call. |
| **Branch coverage ≥ 80%** | Enforced by `--cov-fail-under=80` in CI to catch logical gaps beyond simple line coverage. |
