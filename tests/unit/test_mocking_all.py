import pytest
from unittest.mock import MagicMock

from fastapi_app.services import (
    get_external_data,
    create_user,
    cache_user,
)


# ============================================================
# HTTP MOCK TESTS
# ============================================================

@pytest.mark.asyncio
async def test_http_mock_success(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok"}

    mock_get = mocker.patch(
        "fastapi_app.services.httpx.AsyncClient.get",
        autospec=True,
    )
    mock_get.return_value = mock_response

    result = await get_external_data()

    assert result == {"status": "ok"}
    mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_http_mock_called_with_correct_url(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": 123}

    mock_get = mocker.patch(
        "fastapi_app.services.httpx.AsyncClient.get",
        autospec=True,
    )
    mock_get.return_value = mock_response

    await get_external_data()

    called_url = mock_get.call_args[0][1]
    assert called_url == "https://api.example.com/data"


@pytest.mark.asyncio
async def test_http_mock_failure(mocker):
    mock_get = mocker.patch(
        "fastapi_app.services.httpx.AsyncClient.get",
        autospec=True,
    )

    mock_get.side_effect = Exception("API down")

    with pytest.raises(Exception):
        await get_external_data()

    mock_get.assert_called_once()


# ============================================================
# DATABASE MOCK TESTS
# ============================================================

def test_database_mock_add_and_commit_called(mocker):
    mock_db = mocker.Mock()

    create_user(mock_db, "Ruslan", "ruslan@test.com")

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_database_commit_not_called(mocker):
    mock_db = mocker.Mock()

    mock_db.add({"x": 1})

    mock_db.commit.assert_not_called()


# ============================================================
# REDIS MOCK TESTS
# ============================================================

def test_redis_mock_set_called(mocker):
    mock_redis = mocker.Mock()

    cache_user(mock_redis, "123", "DATA")

    mock_redis.set.assert_called_once_with("123", "DATA")


def test_redis_called_exactly_twice(mocker):
    mock_redis = mocker.Mock()

    cache_user(mock_redis, "1", "A")
    cache_user(mock_redis, "2", "B")

    assert mock_redis.set.call_count == 2


def test_redis_not_called(mocker):
    mock_redis = mocker.Mock()

    mock_redis.set.assert_not_called()