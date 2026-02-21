import pytest
from fastapi.testclient import TestClient
from fastapi_app.main import app


@pytest.fixture
def client():
    return TestClient(app)

def test_get_items_empty(client):
    response = client.get("/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_item(client):
    response = client.post("/users", json={"name": "apple", "email": "apple@example.com"})
    assert response.status_code == 200
    assert response.json()["name"] == "apple"
    assert response.json()["email"] == "apple@example.com"


def test_get_items_after_create(client):
    client.post("/users", json={"name": "banana", "email": "banana@example.com"})
    response = client.get("/users")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_create_multiple_items(client):
    client.post("/users", json={"name": "a", "email": "a@example.com"})
    client.post("/users", json={"name": "b", "email": "b@example.com"})
    response = client.get("/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_invalid_method(client):
    response = client.put("/users")
    assert response.status_code == 405
