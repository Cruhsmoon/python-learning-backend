import pytest


@pytest.fixture(scope="function")
def celery_app():
    """
    Celery app configured for synchronous eager execution.
    Changes are applied before each test and reverted after.
    """
    import src.tasks.celery_app as _celery

    original = {
        "task_always_eager": _celery.app.conf.task_always_eager,
        "task_eager_propagates": _celery.app.conf.task_eager_propagates,
        "broker_url": _celery.app.conf.broker_url,
        "result_backend": _celery.app.conf.result_backend,
    }

    _celery.app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        broker_url="memory://",
        result_backend="cache+memory://",
    )

    yield _celery.app

    _celery.app.conf.update(original)


@pytest.fixture(scope="function")
def fake_redis():
    """In-memory Redis substitute — no real Redis server required."""
    import fakeredis
    server = fakeredis.FakeServer()
    return fakeredis.FakeRedis(server=server, decode_responses=False)
