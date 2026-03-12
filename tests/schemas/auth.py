from src.api.main import TokenResponse
from tests.schemas._base import strict

TOKEN_RESPONSE: dict = strict(TokenResponse.model_json_schema())
