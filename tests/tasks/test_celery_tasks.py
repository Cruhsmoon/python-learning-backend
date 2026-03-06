"""
Celery task tests — no real Redis or message broker required.

All tests rely on:
  celery_app fixture  — task_always_eager=True runs tasks synchronously.
  fake_redis fixture  — in-memory Redis via fakeredis.
  monkeypatch         — replaces _get_redis() and time.sleep where needed.

Test groups:
  1. Synchronous execution   — tasks complete inline, result available immediately.
  2. Redis writes            — store_result persists data in fakeredis.
  3. Retry behaviour         — flaky_task retries up to max_retries times.
  4. Timeout handling        — slow_task raises SoftTimeLimitExceeded when patched.
  5. Error propagation       — exceptions surface at the call site (eager propagates).
"""

import pytest
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

import workers.celery_app as celery_module
from workers.celery_app import (
    add,
    always_fails,
    flaky_task,
    slow_task,
    store_result,
)


# ============================================================ 1. synchronous ==

def test_task_executes_synchronously(celery_app):
    """apply() blocks and returns an already-resolved EagerResult."""
    result = add.apply(args=[3, 4])

    assert result.successful()
    assert result.get() == 7


def test_task_result_accessible_without_get(celery_app):
    """EagerResult.result holds the value without an extra .get() call."""
    result = add.apply(args=[10, 20])

    assert result.result == 30


# ================================================================ 2. redis ==

def test_store_result_writes_correct_value(celery_app, monkeypatch, fake_redis):
    """Task should set the key in Redis and return the stored value."""
    monkeypatch.setattr(celery_module, "_get_redis", lambda: fake_redis)

    result = store_result.apply(args=["greeting", "hello"])

    assert result.get() == "hello"
    assert fake_redis.get("greeting") == b"hello"


def test_store_result_overwrites_existing_key(celery_app, monkeypatch, fake_redis):
    """A second write to the same key replaces the previous value."""
    monkeypatch.setattr(celery_module, "_get_redis", lambda: fake_redis)

    store_result.apply(args=["counter", "first"])
    store_result.apply(args=["counter", "second"])

    assert fake_redis.get("counter") == b"second"


def test_store_result_independent_keys(celery_app, monkeypatch, fake_redis):
    """Multiple keys are stored and retrieved independently."""
    monkeypatch.setattr(celery_module, "_get_redis", lambda: fake_redis)

    store_result.apply(args=["k1", "alpha"])
    store_result.apply(args=["k2", "beta"])

    assert fake_redis.get("k1") == b"alpha"
    assert fake_redis.get("k2") == b"beta"


# ============================================================= 3. retry ==

def test_flaky_task_succeeds_without_retries(celery_app):
    """fail_times=0 means the task succeeds on the first attempt."""
    result = flaky_task.apply(args=[0])

    assert result.get() == "success"


def test_flaky_task_retries_and_succeeds(celery_app):
    """Task retries twice (fail_times=2) and succeeds on the third attempt."""
    result = flaky_task.apply(args=[2])

    assert result.get() == "success"


def test_flaky_task_exhausts_max_retries(celery_app):
    """
    Requesting more retries than max_retries (3) raises an exception.
    Celery raises either MaxRetriesExceededError or the original exc.
    """
    with pytest.raises((MaxRetriesExceededError, ValueError)):
        flaky_task.apply(args=[10])


# =========================================================== 4. timeout ==

def test_slow_task_completes_when_no_sleep(celery_app):
    """With sleep_seconds=0, slow_task returns 'done' immediately."""
    result = slow_task.apply(args=[0])

    assert result.get() == "done"


def test_slow_task_raises_soft_time_limit_exceeded(celery_app, monkeypatch):
    """
    Eager mode does not enforce soft_time_limit automatically; the worker
    delivers the signal in production.  We simulate that signal by patching
    time.sleep to raise SoftTimeLimitExceeded, verifying that the task and
    the test infrastructure handle it correctly.
    """
    def _raise_timeout(_seconds):
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr(celery_module.time, "sleep", _raise_timeout)

    with pytest.raises(SoftTimeLimitExceeded):
        slow_task.apply(args=[99])


# =========================================================== 5. errors ==

def test_error_propagates_to_caller(celery_app):
    """
    With task_eager_propagates=True, exceptions raised inside a task
    bubble up through apply() to the calling code.
    """
    with pytest.raises(RuntimeError, match="Intentional failure"):
        always_fails.apply()


def test_add_with_wrong_type_propagates_error(celery_app):
    """TypeError from adding int + str propagates to the caller."""
    with pytest.raises(TypeError):
        add.apply(args=[1, "string"])  # int + str raises TypeError; apply() re-raises it
