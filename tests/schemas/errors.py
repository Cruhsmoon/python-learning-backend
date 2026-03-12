"""Error response schemas — defined manually for strict QA contract."""

ERROR_422: dict = {
    "type": "object",
    "required": ["detail"],
    "additionalProperties": False,
    "properties": {
        "detail": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["loc", "msg", "type"],
                "additionalProperties": True,
                "properties": {
                    "loc": {
                        "type": "array",
                        "items": {"type": ["string", "integer"]},
                        "minItems": 1,
                    },
                    "msg": {"type": "string"},
                    "type": {"type": "string"},
                },
            },
        }
    },
}

ERROR_401: dict = {
    "type": "object",
    "required": ["detail"],
    "additionalProperties": False,
    "properties": {
        "detail": {"type": "string"},
    },
}

ERROR_403: dict = ERROR_401.copy()
ERROR_409: dict = ERROR_401.copy()
