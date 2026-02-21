import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi_app.main import app, Base, get_db


# ---------- Test DB ----------

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="function")
async def async_client():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    Base.metadata.drop_all(bind=engine)


# ---------- Tests ----------

@pytest.mark.asyncio
async def test_create_user(async_client):
    response = await async_client.post(
        "/users",
        json={"name": "John", "email": "john@example.com"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert data["name"] == "John"
    assert data["email"] == "john@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_users(async_client):
    await async_client.post(
        "/users",
        json={"name": "Alice", "email": "alice@example.com"},
    )

    response = await async_client.get("/users")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_422_validation_error(async_client):
    response = await async_client.post(
        "/users",
        json={"name": "NoEmail"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_404_not_found(async_client):
    response = await async_client.get("/nonexistent")
    assert response.status_code == 404