"""
Consumer contract tests — tests/pact/test_users_consumer.py
============================================================
Defines what the 'users-consumer' expects from the 'users-provider'.

Interactions covered
--------------------
  GET  /users        → 200 list[UserResponse]
  POST /users        → 200 UserResponse (created user)

Pact files are written to tests/pact/pacts/ when the session ends.
Run these before the provider verification tests.
"""

from __future__ import annotations

from pathlib import Path

import allure
import httpx
import pytest
from pact import Consumer, EachLike, Like, Provider

PACT_MOCK_HOST = "localhost"
PACT_MOCK_PORT = 1234
PACT_DIR = str(Path(__file__).parent / "pacts")
LOG_DIR = str(Path(__file__).parent / "logs")

MOCK_URL = f"http://{PACT_MOCK_HOST}:{PACT_MOCK_PORT}"


# ── Pact mock server fixture ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pact():
    """Start pact mock server for this module; write pact file on teardown."""
    p = Consumer("users-consumer").has_pact_with(
        Provider("users-provider"),
        host_name=PACT_MOCK_HOST,
        port=PACT_MOCK_PORT,
        pact_dir=PACT_DIR,
        log_dir=LOG_DIR,
    )
    p.start_service()
    yield p
    p.stop_service()


# ── Consumer tests ────────────────────────────────────────────────────────────

@allure.feature("Pact — Consumer Contracts")
@allure.story("GET /users")
@pytest.mark.contract
def test_get_users_returns_list_of_users(pact) -> None:
    """
    Consumer expects GET /users to return a JSON array where each element
    has at minimum an integer 'id', string 'name', and string 'email'.

    Using EachLike + Like (type-based matching) so the contract is not
    brittle to specific values.
    """
    expected_body = EachLike(
        {
            "id": Like(1),
            "name": Like("Alice"),
            "email": Like("alice@example.com"),
        }
    )

    (
        pact
        .given("users exist")
        .upon_receiving("a GET request for all users")
        .with_request("GET", "/users")
        .will_respond_with(
            200,
            body=expected_body,
            headers={"Content-Type": "application/json"},
        )
    )

    with pact:
        with allure.step("Send GET /users to pact mock server"):
            response = httpx.get(f"{MOCK_URL}/users")

        with allure.step("Assert 200 with list containing required fields"):
            assert response.status_code == 200
            users = response.json()
            assert isinstance(users, list)
            assert len(users) >= 1
            user = users[0]
            assert "id" in user
            assert "name" in user
            assert "email" in user
            assert isinstance(user["id"], int)


@allure.feature("Pact — Consumer Contracts")
@allure.story("POST /users")
@pytest.mark.contract
def test_create_user_returns_user_with_id(pact) -> None:
    """
    Consumer expects POST /users with {name, email} to return the created
    user including a server-assigned integer 'id'.
    """
    request_body = {"name": "Bob", "email": "bob@example.com"}
    expected_body = {
        "id": Like(42),
        "name": "Bob",
        "email": "bob@example.com",
    }

    (
        pact
        .given("user data is valid")
        .upon_receiving("a POST request to create a user")
        .with_request(
            "POST",
            "/users",
            body=request_body,
            headers={"Content-Type": "application/json"},
        )
        .will_respond_with(
            200,
            body=expected_body,
            headers={"Content-Type": "application/json"},
        )
    )

    with pact:
        with allure.step("Send POST /users to pact mock server"):
            response = httpx.post(
                f"{MOCK_URL}/users",
                json=request_body,
                headers={"Content-Type": "application/json"},
            )

        with allure.step("Assert 200 with user object containing all fields"):
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Bob"
            assert data["email"] == "bob@example.com"
            assert isinstance(data["id"], int)
