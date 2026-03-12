"""
Provider verification — tests/pact/test_users_provider.py
==========================================================
Verifies that the 'users-provider' (FastAPI app) satisfies every interaction
recorded in the consumer pact files under tests/pact/pacts/.

Architecture
------------
  1. A lightweight SQLite database is created in-process for isolation.
  2. The real FastAPI app routes are mounted alongside a /_pact/provider_states
     endpoint that seeds or resets the database before each interaction.
  3. A uvicorn server is started in a daemon thread on PROVIDER_PORT.
  4. The Pact Verifier POSTs to /_pact/provider_states, then replays each
     consumer interaction against the running server.

Run AFTER consumer tests so pact files exist:
    pytest tests/pact/test_users_consumer.py -m contract -q
    pytest tests/pact/test_users_provider.py -m contract -q
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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from src.api.main import Base, User, get_db

PROVIDER_PORT = 8765
PROVIDER_URL = f"http://127.0.0.1:{PROVIDER_PORT}"
PACT_DIR = Path(__file__).parent / "pacts"
PACT_FILE = str(PACT_DIR / "users-consumer-users-provider.json")
PROVIDER_STATES_URL = f"{PROVIDER_URL}/_pact/provider_states"

# ── Isolated SQLite for provider tests ───────────────────────────────────────

_DB_FILE = Path(__file__).parent / "_provider_test.db"
_TEST_ENGINE = create_engine(
    f"sqlite:///{_DB_FILE}",
    connect_args={"check_same_thread": False},
)
_TestSession = sessionmaker(bind=_TEST_ENGINE)


def _get_test_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


# ── Provider state setup handler ──────────────────────────────────────────────

async def _provider_states(request: Request) -> JSONResponse:
    """
    Called by the Verifier before each interaction.
    Sets up (or clears) the database to match the declared provider state.
    """
    body = await request.json()
    state: str = body.get("state", "")

    db = _TestSession()
    try:
        if state == "users exist":
            if not db.query(User).first():
                db.add(User(name="Alice", email="alice@example.com"))
                db.commit()
        elif state in ("no users exist", ""):
            db.query(User).delete()
            db.commit()
        # "user data is valid" → no prior state needed for POST
    finally:
        db.close()

    return JSONResponse({"state": state})


# ── Build combined provider + state-setup app ─────────────────────────────────

def _build_provider_app() -> Starlette:
    """Wrap the real FastAPI app with the /_pact/provider_states endpoint."""
    from src.api.main import app as api_app

    # Override the DB dependency to use the isolated SQLite engine
    api_app.dependency_overrides[get_db] = _get_test_db

    Base.metadata.create_all(bind=_TEST_ENGINE)

    return Starlette(
        routes=[
            Route("/_pact/provider_states", _provider_states, methods=["POST"]),
            Mount("/", app=api_app),
        ]
    )


# ── Provider server fixture ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def provider_server():
    """Start provider app in a background thread; yield its base URL."""
    app = _build_provider_app()
    config = uvicorn.Config(
        app, host="127.0.0.1", port=PROVIDER_PORT, log_level="warning"
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait until the server accepts connections (up to 4 s)
    for _ in range(20):
        try:
            httpx.get(f"{PROVIDER_URL}/users", timeout=0.5)
            break
        except Exception:
            time.sleep(0.2)

    yield PROVIDER_URL

    server.should_exit = True
    thread.join(timeout=5)

    # Clean up DB file and dependency override
    from src.api.main import app as api_app
    api_app.dependency_overrides.pop(get_db, None)
    _DB_FILE.unlink(missing_ok=True)


# ── Provider verification test ────────────────────────────────────────────────

@allure.feature("Pact — Provider Verification")
@allure.story("users-provider satisfies users-consumer contract")
@pytest.mark.contract
def test_provider_verifies_consumer_pacts(provider_server: str) -> None:
    """
    Verify every interaction in tests/pact/pacts/ against the live provider.

    Fails if the provider:
      - Returns an unexpected status code
      - Omits a field the consumer declared as required
      - Returns a field with the wrong type
    """
    verifier = Verifier(
        provider="users-provider",
        provider_base_url=provider_server,
    )

    with allure.step(f"Verify pacts from {PACT_FILE}"):
        return_code, _ = verifier.verify_pacts(
            PACT_FILE,
            provider_states_setup_url=PROVIDER_STATES_URL,
            verbose=False,
        )

    assert return_code == 0, (
        "Pact provider verification FAILED — the provider broke the consumer contract.\n"
        f"Pact directory: {PACT_DIR}\n"
        "Run with verbose=True for detailed interaction failures."
    )
