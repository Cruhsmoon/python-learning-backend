"""
Sync integration tests for the /users endpoints.

Uses Starlette's TestClient (synchronous) via the sync_client fixture defined
in tests/conftest.py.  Each test runs inside a transaction that is rolled back
on teardown, so tests are fully isolated from one another.
"""

import pytest

from tests.factories import user_factory


# ================================================================
# POST /users — valid payloads
# ================================================================

def test_create_user_returns_200(sync_client):
    response = sync_client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
    assert response.status_code == 200


def test_create_user_response_has_id(sync_client):
    response = sync_client.post("/users", json={"name": "Bob", "email": "bob@example.com"})
    assert "id" in response.json()


def test_create_user_id_is_integer(sync_client):
    response = sync_client.post("/users", json={"name": "Carol", "email": "carol@example.com"})
    assert isinstance(response.json()["id"], int)


def test_create_user_response_has_name(sync_client):
    payload = {"name": "Dave", "email": "dave@example.com"}
    response = sync_client.post("/users", json=payload)
    assert response.json()["name"] == "Dave"


def test_create_user_response_has_email(sync_client):
    payload = {"name": "Eve", "email": "eve@example.com"}
    response = sync_client.post("/users", json=payload)
    assert response.json()["email"] == "eve@example.com"


def test_create_user_content_type_is_json(sync_client):
    response = sync_client.post("/users", json={"name": "Frank", "email": "frank@example.com"})
    assert response.headers["content-type"].startswith("application/json")


def test_create_user_unicode_name(sync_client):
    payload = {"name": "Ганна Шевченко", "email": "hanna@example.ua"}
    response = sync_client.post("/users", json=payload)
    assert response.status_code == 200
    assert response.json()["name"] == "Ганна Шевченко"


# ================================================================
# POST /users — invalid payloads (expect 422)
# ================================================================

def test_create_empty_body_returns_422(sync_client):
    response = sync_client.post("/users", json={})
    assert response.status_code == 422


def test_create_missing_name_field_returns_422(sync_client):
    response = sync_client.post("/users", json={"email": "noname@example.com"})
    assert response.status_code == 422


def test_create_missing_email_field_returns_422(sync_client):
    response = sync_client.post("/users", json={"name": "NoEmail"})
    assert response.status_code == 422


def test_create_null_name_returns_422(sync_client):
    response = sync_client.post("/users", json={"name": None, "email": "test@example.com"})
    assert response.status_code == 422


def test_create_null_email_returns_422(sync_client):
    response = sync_client.post("/users", json={"name": "User", "email": None})
    assert response.status_code == 422


def test_create_list_as_name_returns_422(sync_client):
    response = sync_client.post("/users", json={"name": [], "email": "test@example.com"})
    assert response.status_code == 422


def test_create_dict_as_email_returns_422(sync_client):
    response = sync_client.post("/users", json={"name": "User", "email": {}})
    assert response.status_code == 422


# ================================================================
# GET /users
# ================================================================

def test_get_users_returns_200(sync_client):
    response = sync_client.get("/users")
    assert response.status_code == 200


def test_get_users_returns_a_list(sync_client):
    response = sync_client.get("/users")
    assert isinstance(response.json(), list)


def test_get_users_newly_created_user_appears(sync_client):
    payload = user_factory()
    sync_client.post("/users", json=payload)

    users = sync_client.get("/users").json()
    emails = [u["email"] for u in users]
    assert payload["email"] in emails


def test_get_users_response_has_required_fields(sync_client):
    sync_client.post("/users", json=user_factory())
    user = sync_client.get("/users").json()[0]
    assert set(user.keys()) >= {"id", "name", "email"}


# ================================================================
# Wrong HTTP methods and unknown routes
# ================================================================

def test_delete_users_method_not_allowed(sync_client):
    response = sync_client.delete("/users")
    assert response.status_code == 405


def test_put_users_method_not_allowed(sync_client):
    response = sync_client.put("/users")
    assert response.status_code == 405


def test_get_nonexistent_route_returns_404(sync_client):
    response = sync_client.get("/nonexistent")
    assert response.status_code == 404


def test_get_user_by_id_not_found(sync_client):
    response = sync_client.get("/users/99999")
    assert response.status_code == 404
