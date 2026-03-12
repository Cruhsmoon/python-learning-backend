from src.api.main import MeResponse
from tests.schemas._base import strict

ME_RESPONSE: dict = strict(MeResponse.model_json_schema())
