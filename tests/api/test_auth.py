"""
JWT authentication tests for GET /users/me and GET /admin/users.

Scenarios covered:
  - valid token              → 200
  - missing token            → 401
  - invalid (garbage) token  → 401
  - expired token            → 401
  - malformed token          → 401
  - wrong signature          → 401
  - wrong algorithm          → 401
  - valid token, wrong role  → 403
"""

from datetime import datetime, timedelta, timezone

import allure
import jwt
import pytest

from src.api.main import SECRET_KEY, ALGORITHM

pytestmark = pytest.mark.asyncio


def _make_token(payload: dict, secret: str = SECRET_KEY, algorithm: str = ALGORITHM) -> str:
    return jwt.encode(payload, secret, algorithm=algorithm)


def _expired_token() -> str:
    return _make_token({
        "sub": "testuser",
        "role": "user",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    })


@allure.feature("Authentication")
@allure.story("Valid token access")
async def test_valid_token_returns_200(async_client, auth_headers):
    with allure.step("GET /users/me with valid Bearer token"):
        response = await async_client.get("/users/me", headers=auth_headers)
    with allure.step("Assert 200 and user payload"):
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["role"] == "user"


@allure.feature("Authentication")
@allure.story("Token rejection — missing header")
async def test_missing_token_returns_401(async_client):
    with allure.step("GET /users/me without Authorization header"):
        response = await async_client.get("/users/me")
    with allure.step("Assert 401"):
        assert response.status_code == 401


@allure.feature("Authentication")
@allure.story("Token rejection — invalid token")
async def test_invalid_token_returns_401(async_client):
    with allure.step("GET /users/me with garbage token"):
        headers = {"Authorization": "Bearer this_is_not_a_valid_jwt"}
        response = await async_client.get("/users/me", headers=headers)
    with allure.step("Assert 401"):
        assert response.status_code == 401


@allure.feature("Authentication")
@allure.story("Token rejection — expired token")
async def test_expired_token_returns_401(async_client):
    with allure.step("GET /users/me with expired token"):
        headers = {"Authorization": f"Bearer {_expired_token()}"}
        response = await async_client.get("/users/me", headers=headers)
    with allure.step("Assert 401 with 'expired' in detail"):
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()


@allure.feature("Authentication")
@allure.story("Token rejection — malformed token")
async def test_malformed_token_returns_401(async_client):
    with allure.step("GET /users/me with malformed segments"):
        headers = {"Authorization": "Bearer aaa.bbb.ccc"}
        response = await async_client.get("/users/me", headers=headers)
    with allure.step("Assert 401"):
        assert response.status_code == 401


@allure.feature("Authentication")
@allure.story("Token rejection — wrong signature")
async def test_wrong_signature_returns_401(async_client):
    with allure.step("GET /users/me with wrong-signature token"):
        token = _make_token(
            {"sub": "testuser", "role": "user"},
            secret="wrong-secret-key-padded-to-meet-hs256-minimum",
        )
        headers = {"Authorization": f"Bearer {token}"}
        response = await async_client.get("/users/me", headers=headers)
    with allure.step("Assert 401"):
        assert response.status_code == 401


@allure.feature("Authentication")
@allure.story("Token rejection — wrong algorithm")
async def test_wrong_algorithm_returns_401(async_client):
    with allure.step("GET /users/me with HS512-signed token"):
        token = _make_token(
            {"sub": "testuser", "role": "user"},
            secret="wrong-algorithm-key-padded-to-meet-hs512-minimum-length-requirement",
            algorithm="HS512",
        )
        headers = {"Authorization": f"Bearer {token}"}
        response = await async_client.get("/users/me", headers=headers)
    with allure.step("Assert 401"):
        assert response.status_code == 401


@allure.feature("Authentication")
@allure.story("Role-based access control")
async def test_regular_user_on_admin_endpoint_returns_403(async_client, auth_headers):
    with allure.step("GET /admin/users as non-admin user"):
        response = await async_client.get("/admin/users", headers=auth_headers)
    with allure.step("Assert 403 Forbidden"):
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()
