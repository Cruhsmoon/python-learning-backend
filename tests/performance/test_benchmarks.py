"""
Microbenchmarks for pure functions using pytest-benchmark.

Run:
    pytest tests/performance/test_benchmarks.py -m benchmark -v --benchmark-verbose

Save baseline:
    pytest tests/performance/test_benchmarks.py -m benchmark \
      --benchmark-save=0001_initial \
      --benchmark-storage=tests/performance/baselines/

Compare against baseline:
    pytest tests/performance/test_benchmarks.py -m benchmark \
      --benchmark-compare=0001_initial \
      --benchmark-storage=tests/performance/baselines/
"""
import pytest

from src.utils.functions import format_price, is_even, normalize_name, validate_email

pytestmark = pytest.mark.benchmark


def test_validate_email_valid(benchmark):
    result = benchmark(validate_email, "user@example.com")
    assert result is True


def test_validate_email_invalid(benchmark):
    result = benchmark(validate_email, "not-an-email")
    assert result is False


def test_format_price(benchmark):
    result = benchmark(format_price, 5.555)
    assert result == "$5.56"


def test_normalize_name(benchmark):
    result = benchmark(normalize_name, "  henry web  ")
    assert result == "Henry Web"


def test_is_even(benchmark):
    result = benchmark(is_even, 42)
    assert result is True
