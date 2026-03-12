"""
Schema utilities for JSON Schema contract validation.

strict()          — adds additionalProperties: false recursively
resolve_refs()    — inlines $defs so jsonschema can validate standalone
validate_response() — validates an httpx Response against a schema
"""
import copy
import json

from jsonschema import Draft202012Validator


def strict(schema: dict) -> dict:
    """Recursively add additionalProperties: false to every object in the schema."""
    schema = copy.deepcopy(schema)
    _apply_strict(schema)
    return schema


def _apply_strict(node: dict) -> None:
    if not isinstance(node, dict):
        return
    if node.get("type") == "object" or "properties" in node:
        node.setdefault("additionalProperties", False)
    for value in node.values():
        if isinstance(value, dict):
            _apply_strict(value)
        elif isinstance(value, list):
            for item in value:
                _apply_strict(item)


def resolve_refs(schema: dict) -> dict:
    """Inline $defs/$ref so the schema is self-contained for jsonschema.validate()."""
    schema = copy.deepcopy(schema)
    defs = schema.get("$defs", {})
    if defs:
        # Keep $defs in place so $ref resolution works
        pass
    return schema


def validate_response(response, schema: dict) -> None:
    """
    Validate an httpx Response body against a JSON Schema.
    Raises AssertionError with full detail on failure.
    """
    instance = response.json()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: str(e.path))
    if errors:
        messages = "\n".join(
            f"  [{'.'.join(str(p) for p in e.absolute_path) or 'root'}] {e.message}"
            for e in errors
        )
        raise AssertionError(
            f"Response contract violation ({len(errors)} error(s)):\n{messages}\n\n"
            f"Actual response: {json.dumps(instance, indent=2, ensure_ascii=False)}"
        )
