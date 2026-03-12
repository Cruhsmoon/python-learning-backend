"""
Contract tests — validate response shapes for all endpoints.

Run:
    pytest tests/api/test_contract.py -m contract -v
"""
import pytest

from tests.schemas import (
    ERROR_401,
    ERROR_403,
    ERROR_422,
    ME_RESPONSE,
    TOKEN_RESPONSE,
    USER_RESPONSE,
    USERS_LIST_RESPONSE,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.contract]


class TestAuthLoginContract:
    async def test_success_response_shape(self, async_client, validate_schema):
        response = await async_client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpass"},
        )
        assert response.status_code == 200
        validate_schema(response, TOKEN_RESPONSE)

    async def test_error_422_shape(self, async_client, validate_schema):
        response = await async_client.post("/auth/login", json={})
        assert response.status_code == 422
        validate_schema(response, ERROR_422)

    async def test_error_401_shape(self, async_client, validate_schema):
        response = await async_client.post(
            "/auth/login",
            json={"username": "nobody", "password": "wrong"},
        )
        assert response.status_code == 401
        validate_schema(response, ERROR_401)


class TestGetMeContract:
    async def test_success_response_shape(self, async_client, auth_headers, validate_schema):
        response = await async_client.get("/users/me", headers=auth_headers)
        assert response.status_code == 200
        validate_schema(response, ME_RESPONSE)

    async def test_error_401_shape(self, async_client, validate_schema):
        response = await async_client.get("/users/me")
        assert response.status_code == 401
        validate_schema(response, ERROR_401)


class TestCreateUserContract:
    async def test_success_response_shape(self, async_client, validate_schema):
        response = await async_client.post(
            "/users",
            json={"name": "Alice", "email": "alice@contract.test"},
        )
        assert response.status_code == 200
        validate_schema(response, USER_RESPONSE)

    async def test_error_422_missing_fields(self, async_client, validate_schema):
        response = await async_client.post("/users", json={})
        assert response.status_code == 422
        validate_schema(response, ERROR_422)

    async def test_error_422_wrong_type(self, async_client, validate_schema):
        response = await async_client.post("/users", json={"name": 123, "email": "a@b.com"})
        assert response.status_code == 422
        validate_schema(response, ERROR_422)


class TestGetUsersContract:
    async def test_empty_list_shape(self, async_client, validate_schema):
        response = await async_client.get("/users")
        assert response.status_code == 200
        validate_schema(response, USERS_LIST_RESPONSE)

    async def test_populated_list_shape(self, async_client, validate_schema):
        await async_client.post("/users", json={"name": "Bob", "email": "bob@contract.test"})
        response = await async_client.get("/users")
        assert response.status_code == 200
        validate_schema(response, USERS_LIST_RESPONSE)
        assert all("id" in u and "name" in u and "email" in u for u in response.json())
