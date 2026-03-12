import pytest

VALID_PAYLOAD = {"name": "Alice Smith", "email": "alice@example.com"}


@pytest.fixture
def valid_payload():
    return VALID_PAYLOAD.copy()
