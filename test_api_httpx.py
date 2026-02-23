import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from factories import user_factory
from fastapi_app.main import app, Base, get_db


# ---------- Test DB ----------

SQLALCHEMY_DATABASE_URL = "sqlite:///test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
async def async_client():
    connection = engine.connect()
    connection.exec_driver_sql("BEGIN")  # real BEGIN at DBAPI level (required for SQLite savepoint rollback)
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    session.close()
    connection.exec_driver_sql("ROLLBACK")
    connection.close()


# ---------- Tests ----------

@pytest.mark.asyncio
async def test_create_user(async_client):
    payload = user_factory()

    response = await async_client.post("/users", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert "id" in data


@pytest.mark.asyncio
async def test_get_users(async_client):
    await async_client.post("/users", json=user_factory())

    response = await async_client.get("/users")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_422_validation_error(async_client):
    response = await async_client.post("/users", json={"name": "NoEmail"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_404_not_found(async_client):
    response = await async_client.get("/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_user_missing_name(async_client):
    payload = user_factory()
    del payload["name"]
    response = await async_client.post("/users", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_multiple_users(async_client):
    before = len((await async_client.get("/users")).json())

    await async_client.post("/users", json=user_factory())
    await async_client.post("/users", json=user_factory())
    await async_client.post("/users", json=user_factory())

    response = await async_client.get("/users")
    assert response.status_code == 200
    assert len(response.json()) == before + 3


@pytest.mark.asyncio
async def test_created_user_has_integer_id(async_client):
    response = await async_client.post("/users", json=user_factory())
    assert response.status_code == 200
    assert isinstance(response.json()["id"], int)


@pytest.mark.asyncio
async def test_get_users_returns_all_fields(async_client):
    await async_client.post("/users", json=user_factory())

    response = await async_client.get("/users")
    user = response.json()[0]
    assert "id" in user
    assert "name" in user
    assert "email" in user


@pytest.mark.asyncio
async def test_empty_body_returns_422(async_client):
    response = await async_client.post("/users", json={})
    assert response.status_code == 422
