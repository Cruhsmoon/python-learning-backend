"""
Request format negative tests — wrong Content-Type, malformed JSON, etc.
"""
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.negative]


async def test_wrong_content_type_form(async_client):
    response = await async_client.post(
        "/users",
        content="name=Alice&email=a%40b.com",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code in (415, 422)


async def test_wrong_content_type_plain_text(async_client):
    response = await async_client.post(
        "/users",
        content=b'{"name": "Alice", "email": "a@b.com"}',
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code in (415, 422)


async def test_malformed_json_unquoted_key(async_client):
    response = await async_client.post(
        "/users",
        content=b'{name: "Alice", "email": "a@b.com"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


async def test_truncated_json(async_client):
    response = await async_client.post(
        "/users",
        content=b'{"name": "Alice"',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


async def test_json_array_instead_of_object(async_client):
    response = await async_client.post(
        "/users",
        json=[{"name": "Alice", "email": "a@b.com"}],
    )
    assert response.status_code == 422


async def test_empty_body_with_json_content_type(async_client):
    response = await async_client.post(
        "/users",
        content=b"",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


async def test_oversized_name_field(async_client):
    payload = {"name": "A" * 100_000, "email": "a@b.com"}
    response = await async_client.post("/users", json=payload)
    assert response.status_code in (200, 413, 422)
