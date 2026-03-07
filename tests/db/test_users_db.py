"""
PostgreSQL database tests using the db_session and pg_async_client fixtures.

All tests run inside a transaction that is rolled back on teardown,
so no test data ever persists in the database.

Test coverage:
  - insert a user and verify the auto-assigned id
  - query back a user by email to verify it exists
  - unique primary-key constraint violation → IntegrityError
  - ON DELETE CASCADE via a test-only table created inside the transaction
  - API creates a user → db_session sees it in PostgreSQL
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from fastapi_app.main import User


# ------------------------------------------------------------------ helpers --

def _insert_user(db_session, name: str, email: str) -> User:
    user = User(name=name, email=email)
    db_session.add(user)
    db_session.flush()  # assigns id without committing to the real DB
    return user


# ------------------------------------------------------------------ tests ----

def test_insert_user(db_session):
    """Inserting a User should assign a non-null integer id."""
    user = _insert_user(db_session, "Alice", "alice@dbtest.com")

    assert user.id is not None
    assert isinstance(user.id, int)


def test_user_exists_after_insert(db_session):
    """A flushed user should be queryable within the same session."""
    user = _insert_user(db_session, "Bob", "bob@dbtest.com")

    fetched = db_session.query(User).filter_by(email="bob@dbtest.com").first()

    assert fetched is not None
    assert fetched.name == "Bob"
    assert fetched.id == user.id


def test_unique_constraint_violation(db_session):
    """
    Attempting to insert a second row with the same primary key raises
    IntegrityError (PostgreSQL enforces PK uniqueness).
    """
    user = _insert_user(db_session, "Charlie", "charlie@dbtest.com")
    user_id = user.id

    # Detach the original object so SQLAlchemy's identity map does not
    # treat the duplicate as an update of the existing row.
    db_session.expunge(user)

    duplicate = User(id=user_id, name="Charlie Clone", email="clone@dbtest.com")
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_cascade_delete(db_session):
    """
    Deleting a parent user cascades to child rows in a related table.

    A temporary child table with ON DELETE CASCADE is created inside this
    transaction.  Because PostgreSQL DDL is transactional, the CREATE TABLE
    is rolled back together with the data when the fixture tears down.
    """
    # Create a child table inside the transaction — rolled back on teardown.
    db_session.execute(text("DROP TABLE IF EXISTS test_user_posts"))
    db_session.execute(text("""
        CREATE TABLE test_user_posts (
            id      SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title   TEXT    NOT NULL
        )
    """))

    # Insert parent user via ORM.
    user = _insert_user(db_session, "Dana", "dana@cascade.com")
    user_id = user.id

    # Insert child row via raw SQL.
    db_session.execute(
        text("INSERT INTO test_user_posts (user_id, title) VALUES (:uid, :t)"),
        {"uid": user_id, "t": "child post"},
    )
    db_session.flush()

    # Verify child exists before the parent is deleted.
    child_before = db_session.execute(
        text("SELECT id FROM test_user_posts WHERE user_id = :uid"),
        {"uid": user_id},
    ).fetchone()
    assert child_before is not None

    # Remove the user from the ORM identity map so that the raw DELETE
    # below does not conflict with the session's internal state.
    db_session.expunge(user)
    db_session.execute(
        text("DELETE FROM users WHERE id = :uid"), {"uid": user_id}
    )
    db_session.flush()

    # ON DELETE CASCADE should have removed the child row automatically.
    child_after = db_session.execute(
        text("SELECT id FROM test_user_posts WHERE user_id = :uid"),
        {"uid": user_id},
    ).fetchone()
    assert child_after is None


# ------------------------------------------------------------------ API+DB --

@pytest.mark.asyncio
async def test_api_create_user_persists_in_db(pg_async_client):
    """
    Creating a user through the HTTP API should persist it in PostgreSQL.

    pg_async_client yields (client, session) where both talk to the same
    PostgreSQL connection inside one transaction that is rolled back at the end.
    """
    client, session = pg_async_client

    payload = {"name": "Eve API", "email": "eve@apidbtest.com"}
    response = await client.post("/users", json=payload)

    assert response.status_code == 200
    user_id = response.json()["id"]

    # Verify via direct DB query — not just the HTTP response.
    user = session.get(User, user_id)
    assert user is not None
    assert user.name == "Eve API"
    assert user.email == "eve@apidbtest.com"
