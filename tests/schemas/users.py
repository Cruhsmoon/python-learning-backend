from src.api.main import UserResponse
from tests.schemas._base import strict

_USER_BASE = UserResponse.model_json_schema()

USER_RESPONSE: dict = strict(_USER_BASE)

USERS_LIST_RESPONSE: dict = {
    "type": "array",
    "items": USER_RESPONSE,
}
