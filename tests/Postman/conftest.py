import os
import pytest
import httpx


@pytest.fixture(scope="session")
def base_url():
    url = os.getenv("BASE_URL")
    if not url:
        raise RuntimeError("BASE_URL not defined in environment")
    return url.rstrip("/")


@pytest.fixture
async def client(base_url):
    async with httpx.AsyncClient(base_url=base_url) as c:
        yield c


@pytest.fixture
def json_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
