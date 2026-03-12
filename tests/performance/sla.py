"""
SLA configuration — per-endpoint response time thresholds.

Adding a new endpoint = one line here. Tests never contain raw millisecond numbers.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SLA:
    mean_ms: float          # mean of N samples must not exceed this
    max_ms: float           # no single sample may exceed this (soft p99)
    samples: int = 5        # number of measured requests (after warm-up)
    warmup: int = 1         # discarded warm-up requests


ENDPOINT_SLA: dict[str, SLA] = {
    "POST /auth/login":  SLA(mean_ms=150, max_ms=300),
    "GET /users/me":     SLA(mean_ms=80,  max_ms=200),
    "GET /users":        SLA(mean_ms=200, max_ms=400),
    "POST /users":       SLA(mean_ms=180, max_ms=350),
    "GET /admin/users":  SLA(mean_ms=250, max_ms=500),
}

DEFAULT_SLA = SLA(mean_ms=400, max_ms=800)
