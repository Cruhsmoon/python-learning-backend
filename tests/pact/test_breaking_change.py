"""
Breaking change demonstration — tests/pact/test_breaking_change.py
==================================================================
Shows that removing the 'email' field from UserResponse is caught by Pact
BEFORE the change reaches production.

How it works
------------
  1. A deliberately broken provider is started — its GET /users and POST /users
     routes omit the 'email' field from every response.
  2. The Pact Verifier replays the consumer pact interactions against this
     broken server.
  3. Verification FAILS because the consumer declared it expects 'email'.
  4. The test asserts that the failure was detected, proving the safety net works.

Run after consumer tests (pact files must exist):
    pytest tests/pact/test_users_consumer.py -m contract -q
    pytest tests/pact/test_breaking_change.py -m contract -v
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import allure
import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from pact import Verifier
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

BREAKING_PORT = 8766
BREAKING_URL = f"http://127.0.0.1:{BREAKING_PORT}"
PACT_FILE = str(Path(__file__).parent / "pacts" / "users-consumer-users-provider.json")
STATES_URL = f"{BREAKING_URL}/_pact/provider_states"


# ── Broken provider — 'email' field intentionally removed ────────────────────

class _BrokenUserResponse(BaseModel):
    """UserResponse with 'email' omitted — simulates a developer removing a field."""
    id: int
    name: str
    # email: str  ← deliberately removed


def _build_broken_provider() -> Starlette:
    broken = FastAPI()

    @broken.get("/users", response_model=list[_BrokenUserResponse])
    def _get_users():
        # Returns users WITHOUT the 'email' field
        return [{"id": 1, "name": "Alice"}]

    @broken.post("/users", response_model=_BrokenUserResponse)
    async def _create_user(request: Request):
        body = await request.json()
        # Returns created user WITHOUT the 'email' field
        return {"id": 2, "name": body.get("name", "")}

    async def _provider_states(request: Request) -> JSONResponse:
        body = await request.json()
        return JSONResponse({"state": body.get("state", "")})

    return Starlette(
        routes=[
            Route("/_pact/provider_states", _provider_states, methods=["POST"]),
            Mount("/", app=broken),
        ]
    )


# ── Broken provider server fixture ────────────────────────────────────────────

@pytest.fixture(scope="module")
def broken_provider_server():
    app = _build_broken_provider()
    config = uvicorn.Config(
        app, host="127.0.0.1", port=BREAKING_PORT, log_level="warning"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    for _ in range(20):
        try:
            httpx.get(f"{BREAKING_URL}/users", timeout=0.5)
            break
        except Exception:
            time.sleep(0.2)

    yield BREAKING_URL

    server.should_exit = True
    thread.join(timeout=5)


# ── Breaking change test ──────────────────────────────────────────────────────

@allure.feature("Pact — Breaking Change Detection")
@allure.story("Removing 'email' from UserResponse is caught by Pact")
@pytest.mark.contract
def test_removing_email_field_is_detected_as_breaking_change(
    broken_provider_server: str,
) -> None:
    """
    A provider that removes the 'email' field MUST fail Pact verification.

    This test proves that consumer-driven contracts catch breaking API changes
    before they reach production — the classic Pact value proposition.

    The verification is expected to return a non-zero exit code.
    If it returns 0 (success), our contract is not strict enough.
    """
    verifier = Verifier(
        provider="users-provider",
        provider_base_url=broken_provider_server,
    )

    with allure.step("Run Pact verification against the broken provider"):
        return_code, _ = verifier.verify_pacts(
            PACT_FILE,
            provider_states_setup_url=STATES_URL,
            verbose=False,
        )

    with allure.step("Assert that verification detected the breaking change"):
        assert return_code != 0, (
            "Expected Pact verification to FAIL (the 'email' field was removed), "
            "but verification unexpectedly PASSED. "
            "This means the consumer contract is not checking for 'email' — "
            "tighten the EachLike/Like matchers in test_users_consumer.py."
        )

    allure.attach(
        "Pact correctly detected that removing 'email' from UserResponse "
        "breaks the consumer contract.\n\n"
        "This is the intended outcome: the CI pipeline would block the "
        "breaking change from being merged.",
        name="Breaking change detection result",
        attachment_type=allure.attachment_type.TEXT,
    )
