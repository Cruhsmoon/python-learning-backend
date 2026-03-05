import os
import pytest
import httpx


@pytest.fixture(scope="session")
def base_url():
    return os.getenv("BASE_URL", "").rstrip("/")


@pytest.fixture
async def client(base_url, async_client):
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
