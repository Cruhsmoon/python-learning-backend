import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import src.api.main as _app_module
from src.api.main import app, Base, get_db
from httpx import AsyncClient, ASGITransport

PG_DATABASE_URL = os.getenv("PG_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")


@pytest.fixture(scope="session")
def pg_schema():
    """Creates the app schema in real PostgreSQL once per test session.

    Needed because patch_production_engine (autouse, session-scoped) redirects
    Base.metadata.create_all() to the SQLite test engine, so PostgreSQL never
    gets its tables created automatically.  This fixture fills that gap.
    """
    engine = create_engine(PG_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    yield


@pytest.fixture(scope="function")
def db_session(pg_schema):
    """
    SQLAlchemy Session connected to real PostgreSQL.

    Lifecycle:
      1. Create a new engine and connection.
      2. Start a DBAPI-level transaction (BEGIN).
      3. Bind a Session to that connection.
      4. Yield the session — tests use flush(), not commit().
      5. Roll back on teardown — no data persists between tests.
    """
    engine = create_engine(PG_DATABASE_URL)
    connection = engine.connect()
    connection.exec_driver_sql("BEGIN")
    session = Session(bind=connection)

    yield session

    session.close()
    connection.exec_driver_sql("ROLLBACK")
    connection.close()
    engine.dispose()


@pytest.fixture(scope="function")
async def pg_async_client(pg_schema):
    """
    AsyncClient that drives the FastAPI app against real PostgreSQL.

    The session-scoped patch_production_engine autouse fixture has already
    replaced _app_module.engine with SQLite.  This fixture temporarily
    restores the real PostgreSQL engine for the duration of one test, then
    puts the SQLite engine back so other tests are unaffected.

    Yields (client, session) so the caller can both make HTTP requests and
    query the database directly to verify persistence.
    """
    pg_engine = create_engine(PG_DATABASE_URL)
    connection = pg_engine.connect()
    connection.exec_driver_sql("BEGIN")
    # create_savepoint mode lets route-level db.commit() land inside the outer
    # transaction instead of committing to the database for real.
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    # Temporarily override the SQLite patch with the real PostgreSQL engine.
    saved_engine = _app_module.engine
    _app_module.engine = pg_engine

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, session

    app.dependency_overrides.pop(get_db, None)
    session.close()
    connection.exec_driver_sql("ROLLBACK")
    connection.close()
    pg_engine.dispose()
    _app_module.engine = saved_engine  # restore SQLite patch for remaining tests
