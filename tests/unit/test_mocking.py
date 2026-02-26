import pytest
import httpx
from unittest.mock import MagicMock, AsyncMock

from fastapi_app.services import fetch_github_user, save_user, get_cached_user, cache_user


# ---------- External HTTP call ----------

@pytest.mark.asyncio
async def test_fetch_github_user_success(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"login": "octocat", "id": 1}
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    mocker.patch("fastapi_app.services.httpx.AsyncClient", return_value=mock_client)

    result = await fetch_github_user("octocat")

    assert result == {"login": "octocat", "id": 1}
    mock_client.get.assert_called_once_with("https://api.github.com/users/octocat")


@pytest.mark.asyncio
async def test_fetch_github_user_http_error(mocker):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404 Not Found",
        request=MagicMock(),
        response=MagicMock(),
    )

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    mocker.patch("fastapi_app.services.httpx.AsyncClient", return_value=mock_client)

    with pytest.raises(httpx.HTTPStatusError):
        await fetch_github_user("nonexistent-user-xyz")

    mock_client.get.assert_called_once_with(
        "https://api.github.com/users/nonexistent-user-xyz"
    )


# ---------- Database interaction ----------

def test_save_user_calls_db_with_correct_data(mocker):
    mock_db = MagicMock()

    save_user(mock_db, name="Alice", email="alice@example.com")

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

    added_user = mock_db.add.call_args[0][0]
    assert added_user.name == "Alice"
    assert added_user.email == "alice@example.com"


def test_save_user_commit_not_called_on_add_error(mocker):
    mock_db = MagicMock()
    mock_db.add.side_effect = Exception("DB connection lost")

    with pytest.raises(Exception, match="DB connection lost"):
        save_user(mock_db, name="Bob", email="bob@example.com")

    mock_db.commit.assert_not_called()


# ---------- Redis ----------

def test_get_cached_user_hit(mocker):
    mock_redis = MagicMock()
    mock_redis.get.return_value = '{"id": 1, "name": "Alice"}'

    result = get_cached_user(mock_redis, user_id=1)

    assert result == '{"id": 1, "name": "Alice"}'
    mock_redis.get.assert_called_once_with("user:1")


def test_get_cached_user_miss(mocker):
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    result = get_cached_user(mock_redis, user_id=99)

    assert result is None
    mock_redis.get.assert_called_once_with("user:99")


def test_cache_user_calls_set_with_correct_args(mocker):
    mock_redis = MagicMock()

    cache_user(mock_redis, "user:1", '{"id": 1, "name": "Alice"}')

    mock_redis.set.assert_called_once_with("user:1", '{"id": 1, "name": "Alice"}')
