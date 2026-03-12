"""
Security tests — SQL injection, XSS, SSTI, null bytes.

Injection payloads must be stored verbatim (SQLAlchemy parameterizes queries)
and must never cause 5xx errors.
"""
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.negative, pytest.mark.security]


INJECTION_CASES = [
    ("sql_classic",    "'; DROP TABLE users; --"),
    ("sql_union",      "' UNION SELECT 1,2,3--"),
    ("xss_script",     "<script>alert(1)</script>"),
    ("xss_event",      '" onmouseover="alert(1)'),
    ("ssti_jinja",     "{{7*7}}"),
    ("ssti_mako",      "${7*7}"),
    ("path_traversal", "../../../etc/passwd"),
    ("null_byte_str",  "Alice\x00Bob"),
]


@pytest.mark.parametrize("case_id, value", INJECTION_CASES, ids=[c[0] for c in INJECTION_CASES])
async def test_injection_payload(async_client, case_id, value):
    """
    Injection payloads must not cause 5xx.
    If accepted (200), the stored value must equal the input verbatim.
    """
    payload = {"name": value, "email": f"{case_id}@sec.test"}
    response = await async_client.post("/users", json=payload)

    assert response.status_code != 500, (
        f"[{case_id}] Server error — possible injection vulnerability"
    )
    assert response.status_code in (200, 201, 400, 422), (
        f"[{case_id}] Unexpected status {response.status_code}"
    )

    if response.status_code in (200, 201):
        assert response.json()["name"] == value, (
            f"[{case_id}] Value was mutated during storage"
        )
