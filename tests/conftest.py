import pytest
import pytest_html
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fastapi_app.main import app, Base, get_db


# ---------- Session-scoped engine: created once, tables created once ----------

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


# ---------- Function-scoped async client with transaction rollback ----------

@pytest.fixture(scope="function")
async def async_client(request, test_engine):
    connection = test_engine.connect()
    connection.exec_driver_sql("BEGIN")  # real BEGIN at DBAPI level (required for SQLite savepoint rollback)
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    # Capture DB state before rollback — picked up by pytest_runtest_makereport below
    request.node._db_snapshot_html = db_rows_as_html(session)

    session.close()
    connection.exec_driver_sql("ROLLBACK")
    connection.close()


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
