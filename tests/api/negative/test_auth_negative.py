"""
Negative authentication tests for POST /auth/login.

Covers: missing fields, wrong credentials, malformed tokens.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from src.api.main import SECRET_KEY, ALGORITHM

pytestmark = [pytest.mark.asyncio, pytest.mark.negative]


def _expired_token() -> str:
    return jwt.encode(
        {"sub": "testuser", "role": "user", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        SECRET_KEY, algorithm=ALGORITHM,
    )


def _ghost_token() -> str:
    return jwt.encode({"sub": "ghost", "role": "user"}, SECRET_KEY, algorithm=ALGORITHM)


AUTH_CASES = [
    ({},                                                    "Missing or invalid", "no_header"),
    ({"Authorization": "Bearer "},                          "Invalid token",      "empty_bearer"),
    ({"Authorization": "Token abc123"},                     "Missing or invalid", "wrong_scheme"),
    ({"Authorization": "Bearer aaa.bbb.ccc"},               "Invalid token",      "garbage_token"),
    ({"Authorization": f"Bearer {_expired_token()}"},       "Token has expired",  "expired_token"),
    ({"Authorization": f"Bearer {_ghost_token()}"},         "User not found",     "unknown_sub"),
]


@pytest.mark.parametrize("headers, expected_detail, case_id", AUTH_CASES, ids=[c[2] for c in AUTH_CASES])
async def test_get_me_unauthorized(async_client, valid_payload, headers, expected_detail, case_id):
    response = await async_client.get("/users/me", headers=headers)
    assert response.status_code == 401
    assert expected_detail in response.json()["detail"]


@pytest.mark.parametrize("payload, case_id", [
    ({},                                                  "empty_body"),
    ({"username": "testuser"},                            "missing_password"),
    ({"password": "testpass"},                            "missing_username"),
    ({"username": "nobody", "password": "wrong"},         "wrong_credentials"),
    ({"username": None, "password": "testpass"},          "null_username"),
    ({"username": "testuser", "password": None},          "null_password"),
], ids=lambda x: x if isinstance(x, str) else "")
async def test_login_negative(async_client, payload, case_id):
    response = await async_client.post("/auth/login", json=payload)
    assert response.status_code in (401, 422), (
        f"[{case_id}] Expected 401 or 422, got {response.status_code}"
    )
