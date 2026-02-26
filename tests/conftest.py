import pytest
import pytest_html
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import fastapi_app.main as _app_module
from fastapi_app.main import app, Base, get_db


# ---------- Session-scoped SQLite engine ----------

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


# ---------- Swap production engine for SQLite across the whole session ----------
#
# Why autouse + session scope?
# fastapi_app/main.py calls Base.metadata.create_all(bind=engine) inside the
# lifespan handler.  That handler runs every time an ASGI client starts
# (AsyncClient via ASGITransport, or TestClient as context manager).
# By patching the module-level `engine` attribute once at session start we
# ensure every lifespan invocation uses SQLite instead of PostgreSQL, so tests
# work without a running database server.

@pytest.fixture(scope="session", autouse=True)
def patch_production_engine(test_engine):
    original = _app_module.engine
    _app_module.engine = test_engine
    yield
    _app_module.engine = original


# ---------- DB snapshot helper for HTML report ----------

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


# ---------- Async client — per-test transaction rollback ----------
#
# Uses a real DBAPI-level BEGIN so that SQLite savepoints work correctly.
# The savepoint lets each request's commit land inside the transaction;
# the outer ROLLBACK at teardown erases everything, keeping tests isolated.

@pytest.fixture(scope="function")
async def async_client(request, test_engine):
    connection = test_engine.connect()
    connection.exec_driver_sql("BEGIN")
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    request.node._db_snapshot_html = db_rows_as_html(session)

    session.close()
    connection.exec_driver_sql("ROLLBACK")
    connection.close()
    app.dependency_overrides.pop(get_db, None)


# ---------- Sync client — per-test transaction rollback ----------
#
# Same isolation strategy as async_client but using Starlette's synchronous
# TestClient.  TestClient runs the ASGI lifespan when used as a context
# manager; because patch_production_engine has already replaced the module
# engine with SQLite, the lifespan create_all() is a no-op (tables exist).

@pytest.fixture(scope="function")
def sync_client(test_engine):
    connection = test_engine.connect()
    connection.exec_driver_sql("BEGIN")
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    # Do NOT use TestClient as a context manager here.
    # The context manager runs the ASGI lifespan, which calls
    # Base.metadata.create_all(bind=engine).  With StaticPool there is only
    # one DBAPI connection; create_all acquires it and issues an internal
    # COMMIT, which silently ends our outer BEGIN transaction and makes the
    # teardown ROLLBACK fail.  Tables are already created by the session-scoped
    # test_engine fixture, so skipping the lifespan is safe.
    client = TestClient(app, raise_server_exceptions=True)
    yield client

    session.close()
    connection.exec_driver_sql("ROLLBACK")
    connection.close()
    app.dependency_overrides.pop(get_db, None)


# ---------- HTML report: attach DB snapshot to each test ----------

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
