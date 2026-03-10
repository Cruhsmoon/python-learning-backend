import time

import redis
from celery import Celery

REDIS_URL = "redis://localhost:6379/0"

app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)


def _get_redis() -> redis.Redis:
    """Returns a Redis client. Replaced by fakeredis in tests via monkeypatch."""
    return redis.Redis.from_url(REDIS_URL)


# -------------------- Tasks --------------------

@app.task
def add(x: int, y: int) -> int:
    """Returns the sum of two integers."""
    return x + y


@app.task
def store_result(key: str, value: str) -> str:
    """Writes value to Redis under key and returns the value."""
    r = _get_redis()
    r.set(key, value)
    return value


@app.task(bind=True, max_retries=3, default_retry_delay=0)
def flaky_task(self, fail_times: int = 0) -> str:
    """
    Fails fail_times times via self.retry(), then returns 'success'.
    Raises MaxRetriesExceededError if fail_times exceeds max_retries.
    """
    if self.request.retries < fail_times:
        # throw=False tells Celery to execute the retry inline (eager mode)
        # rather than raising a Retry exception that would escape apply().
        return self.retry(
            exc=ValueError(f"Simulated failure (retry {self.request.retries})"),
            countdown=0,
            throw=False,
        )
    return "success"


@app.task
def always_fails() -> None:
    """Always raises RuntimeError — used to test error propagation."""
    raise RuntimeError("Intentional failure")


@app.task(soft_time_limit=1)
def slow_task(sleep_seconds: float = 0) -> str:
    """Sleeps for sleep_seconds then returns 'done'. Has a 1-second soft limit."""
    time.sleep(sleep_seconds)
    return "done"
