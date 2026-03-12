import json
import os
import sys
from pathlib import Path

import allure
import pytest
import pytest_html
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import src.api.main as _app_module
from src.api.main import app, Base, get_db


# ── Worker identity (xdist) ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def worker_id() -> str:
    """xdist worker id, or 'main' when running without xdist."""
    return os.environ.get("PYTEST_XDIST_WORKER", "main")


@pytest.fixture(scope="session")
def worker_tmp_dir(tmp_path_factory, worker_id: str) -> Path:
    """Temporary directory unique to this worker."""
    return tmp_path_factory.mktemp(f"worker_{worker_id}")


# ── Session-scoped SQLite engine ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def patch_production_engine(test_engine):
    original = _app_module.engine
    _app_module.engine = test_engine
    yield
    _app_module.engine = original


# ── Allure environment info ───────────────────────────────────────────────────

def _pkg_version(name: str) -> str:
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return "unknown"


@pytest.fixture(scope="session", autouse=True)
def allure_environment():
    """Write environment.properties to allure-results/ after the session."""
    yield

    alluredir = os.environ.get("ALLURE_RESULTS_DIR", "allure-results")
    if not os.path.isdir(alluredir):
        return

    props = {
        "Python": sys.version.split()[0],
        "FastAPI": _pkg_version("fastapi"),
        "pytest": _pkg_version("pytest"),
        "DB": "SQLite in-memory (unit/api) / PostgreSQL (integration)",
        "Git.SHA": os.environ.get("GITHUB_SHA", "local"),
        "Git.Branch": os.environ.get("GITHUB_REF_NAME", "local"),
        "CI": os.environ.get("CI", "false"),
    }

    with open(os.path.join(alluredir, "environment.properties"), "w") as f:
        for key, value in props.items():
            f.write(f"{key}={value}\n")


# ── DB helpers ────────────────────────────────────────────────────────────────

def db_rows_as_html(session: Session) -> str:
    rows = session.execute(text("SELECT id, name, email FROM users")).fetchall()
    if not rows:
        return "<p><em>No rows in users table for this test.</em></p>"
    header = "<tr><th>id</th><th>name</th><th>email</th></tr>"
    body = "".join(
        f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td></tr>" for r in rows
    )
    return (
        "<table border='1' cellpadding='4' cellspacing='0' "
        "style='border-collapse:collapse;font-size:13px'>"
        f"{header}{body}</table>"
    )


def _attach_db_snapshot_to_allure(session: Session) -> None:
    rows = session.execute(text("SELECT id, name, email FROM users")).fetchall()
    if not rows:
        return
    lines = ["id,name,email"] + [f"{r[0]},{r[1]},{r[2]}" for r in rows]
    allure.attach(
        "\n".join(lines),
        name="DB snapshot (users)",
        attachment_type=allure.attachment_type.CSV,
    )


# ── httpx event hooks for Allure request/response logging ────────────────────

async def _log_request(request) -> None:
    body = ""
    if request.content:
        try:
            body = json.dumps(json.loads(request.content), indent=2, ensure_ascii=False)
        except Exception:
            body = request.content.decode("utf-8", errors="replace")
    allure.attach(
        f"{request.method} {request.url}\n\nHeaders:\n"
        f"{json.dumps(dict(request.headers), indent=2)}\n\nBody:\n{body}",
        name=f"→ {request.method} {request.url.path}",
        attachment_type=allure.attachment_type.TEXT,
    )


async def _log_response(response) -> None:
    await response.aread()
    try:
        body = json.dumps(response.json(), indent=2, ensure_ascii=False)
        attachment_type = allure.attachment_type.JSON
    except Exception:
        body = response.text
        attachment_type = allure.attachment_type.TEXT
    allure.attach(
        body,
        name=f"← {response.status_code} {response.request.url.path}",
        attachment_type=attachment_type,
    )


# ── Async client ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
async def async_client(request, test_engine):
    connection = test_engine.connect()
    connection.exec_driver_sql("BEGIN")
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.event_hooks["request"].append(_log_request)
        client.event_hooks["response"].append(_log_response)
        yield client

    request.node._db_snapshot_html = db_rows_as_html(session)
    _attach_db_snapshot_to_allure(session)

    session.close()
    connection.exec_driver_sql("ROLLBACK")
    connection.close()
    app.dependency_overrides.pop(get_db, None)


# ── Sync client ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def sync_client(test_engine):
    connection = test_engine.connect()
    connection.exec_driver_sql("BEGIN")
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app, raise_server_exceptions=True)
    yield client

    session.close()
    connection.exec_driver_sql("ROLLBACK")
    connection.close()
    app.dependency_overrides.pop(get_db, None)


# ── Auth fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
async def auth_token(async_client):
    response = await async_client.post(
        "/auth/login",
        json={"username": "testuser", "password": "testpass"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ── JSON Schema validation fixture ────────────────────────────────────────────

@pytest.fixture
def validate_schema():
    """
    Validates an httpx Response body against a JSON Schema dict.

    Usage:
        validate_schema(response, USER_RESPONSE)
    """
    from tests.schemas._base import validate_response as _validate

    def _check(response, schema: dict) -> None:
        _validate(response, schema)

    return _check


# ── HTML report: DB snapshot attachment ──────────────────────────────────────

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "teardown":
        db_html = getattr(item, "_db_snapshot_html", None)
        if db_html:
            report.extras = getattr(report, "extras", []) + [
                pytest_html.extras.html(db_html)
            ]
