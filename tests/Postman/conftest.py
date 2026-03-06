import os
import pytest
import httpx


@pytest.fixture(scope="session")
def base_url():
    return os.getenv("BASE_URL", "").rstrip("/")


@pytest.fixture
async def client(base_url, async_client):
    """
    When BASE_URL is set (via --envfile or environment), send requests to the
    live server at that URL.  Otherwise fall back to the in-process ASGI client
    so postman tests pass in the full suite without a running server.
    """
    if base_url:
        async with httpx.AsyncClient(base_url=base_url) as c:
            yield c
    else:
        yield async_client


@pytest.fixture
def json_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
