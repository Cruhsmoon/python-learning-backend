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

import jwt
import pytest

from src.api.main import SECRET_KEY, ALGORITHM


# ------------------------------------------------------------------ helpers --

def _make_token(payload: dict, secret: str = SECRET_KEY, algorithm: str = ALGORITHM) -> str:
    return jwt.encode(payload, secret, algorithm=algorithm)


def _expired_token() -> str:
    return _make_token({
        "sub": "testuser",
        "role": "user",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    })


# ------------------------------------------------------------------ tests ----

@pytest.mark.asyncio
async def test_valid_token_returns_200(async_client, auth_headers):
    response = await async_client.get("/users/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["role"] == "user"


@pytest.mark.asyncio
async def test_missing_token_returns_401(async_client):
    response = await async_client.get("/users/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_returns_401(async_client):
    headers = {"Authorization": "Bearer this_is_not_a_valid_jwt"}
    response = await async_client.get("/users/me", headers=headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_returns_401(async_client):
    headers = {"Authorization": f"Bearer {_expired_token()}"}
    response = await async_client.get("/users/me", headers=headers)

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_malformed_token_returns_401(async_client):
    # Three dot-separated segments but not valid base64-encoded JWT parts
    headers = {"Authorization": "Bearer aaa.bbb.ccc"}
    response = await async_client.get("/users/me", headers=headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_wrong_signature_returns_401(async_client):
    token = _make_token(
        {"sub": "testuser", "role": "user"},
        secret="wrong-secret-key-padded-to-meet-hs256-minimum",  # ≥ 32 bytes
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.get("/users/me", headers=headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_wrong_algorithm_returns_401(async_client):
    token = _make_token(
        {"sub": "testuser", "role": "user"},
        secret="wrong-algorithm-key-padded-to-meet-hs512-minimum-length-requirement",  # ≥ 64 bytes
        algorithm="HS512",
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.get("/users/me", headers=headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_regular_user_on_admin_endpoint_returns_403(async_client, auth_headers):
    # auth_headers belong to "testuser" (role=user), not admin
    response = await async_client.get("/admin/users", headers=auth_headers)

    assert response.status_code == 403
    assert "admin" in response.json()["detail"].lower()
