import pytest


@pytest.mark.asyncio
async def test_get_users(client):
    response = await client.get(
        "/users",
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload, expected_status",
    [
        (
            {"name": "Test User", "email": "test@example.com"},
            200,
        ),
        (
            {},  # validation error
            422,
        ),
    ],
)
async def test_create_user(client, json_headers, payload, expected_status):
    response = await client.post(
        "/users",
        headers=json_headers,
        json=payload,
    )

    assert response.status_code == expected_status
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()

    if expected_status == 422:
        assert "detail" in data
        assert isinstance(data["detail"], list)