import pytest

from tests.factories import user_factory


# ---------- POST /users: valid payloads ----------

@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"name": "Alice Smith", "email": "alice@example.com"},
    {"name": "Іван Франко", "email": "ivan@example.ua"},
    {"name": "José García", "email": "jose@example.es"},
    {"name": "李伟",         "email": "li.wei@example.cn"},
    {"name": "A" * 100,     "email": "long@example.com"},
], ids=[
    "ascii_name",
    "cyrillic_name",
    "accented_latin_name",
    "cjk_name",
    "100_char_name",
])
async def test_create_user_valid(async_client, payload):
    response = await async_client.post("/users", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert isinstance(data["id"], int)


# ---------- POST /users: invalid payloads ----------

@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {},
    {"name": "NoEmail"},
    {"email": "noname@example.com"},
    {"name": None,   "email": "null@example.com"},
    {"name": "User", "email": None},
    {"name": [],     "email": "test@example.com"},
    {"name": "User", "email": {}},
], ids=[
    "empty_body",
    "missing_email",
    "missing_name",
    "null_name",
    "null_email",
    "list_as_name",
    "dict_as_email",
])
async def test_create_user_invalid(async_client, payload):
    response = await async_client.post("/users", json=payload)

    assert response.status_code == 422


# ---------- GET /users: count grows by N ----------

@pytest.mark.asyncio
@pytest.mark.parametrize("count", [1, 2, 3, 5], ids=[
    "create_1_user",
    "create_2_users",
    "create_3_users",
    "create_5_users",
])
async def test_bulk_create_users(async_client, count):
    before = len((await async_client.get("/users")).json())

    for _ in range(count):
        await async_client.post("/users", json=user_factory())

    response = await async_client.get("/users")

    assert response.status_code == 200
    assert len(response.json()) == before + count


# ---------- GET /users: response shape ----------

@pytest.mark.asyncio
async def test_get_users_response_shape(async_client):
    await async_client.post("/users", json=user_factory())

    response = await async_client.get("/users")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    user = response.json()[0]
    assert set(user.keys()) >= {"id", "name", "email"}


# ---------- Negative: wrong routes and methods ----------

@pytest.mark.asyncio
@pytest.mark.parametrize("method, url, expected_status", [
    ("GET",    "/nonexistent", 404),
    ("GET",    "/users/9999",  404),
    ("DELETE", "/users",       405),
    ("PUT",    "/users",       405),
    ("PATCH",  "/users",       405),
], ids=[
    "GET_unknown_route",
    "GET_nonexistent_user",
    "DELETE_users_not_allowed",
    "PUT_users_not_allowed",
    "PATCH_users_not_allowed",
])
async def test_invalid_routes_and_methods(async_client, method, url, expected_status):
    response = await async_client.request(method, url)

    assert response.status_code == expected_status
