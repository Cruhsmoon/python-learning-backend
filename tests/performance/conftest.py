import statistics
from collections.abc import Callable, Coroutine
from typing import Any

import pytest

from tests.performance.sla import DEFAULT_SLA, ENDPOINT_SLA, SLA


@pytest.fixture
def assert_sla():
    """
    Measures response time over N samples and asserts against SLA config.

    Usage:
        times = await assert_sla(
            async_client.get, "/users/me",
            headers=auth_headers,
            sla_key="GET /users/me",
        )
    """
    async def _check(
        method: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        sla_key: str,
        **kwargs: Any,
    ) -> list[float]:
        sla: SLA = ENDPOINT_SLA.get(sla_key, DEFAULT_SLA)

        # Warm-up: prime connection pools / JIT paths
        for _ in range(sla.warmup):
            await method(*args, **kwargs)

        times_ms: list[float] = []
        for _ in range(sla.samples):
            response = await method(*args, **kwargs)
            times_ms.append(response.elapsed.total_seconds() * 1000)

        mean_ms = statistics.mean(times_ms)
        max_ms = max(times_ms)

        assert mean_ms <= sla.mean_ms, (
            f"[{sla_key}] mean={mean_ms:.1f}ms exceeds SLA={sla.mean_ms}ms  "
            f"samples={[f'{t:.1f}' for t in times_ms]}"
        )
        assert max_ms <= sla.max_ms, (
            f"[{sla_key}] max={max_ms:.1f}ms exceeds SLA={sla.max_ms}ms  "
            f"samples={[f'{t:.1f}' for t in times_ms]}"
        )
        return times_ms

    return _check
