import threading
import time

import pytest
from sqlalchemy.exc import OperationalError

from ai_meeting_companion.config import DbSettings
from ai_meeting_companion.core.orchestrator import _bounded
from ai_meeting_companion.session.store import open_store


def _down() -> OperationalError:
    return OperationalError("connect", {}, ConnectionRefusedError("postgres is starting"))


def test_open_store_retries_until_postgres_is_up():
    calls = []

    def factory(db):
        calls.append(1)
        if len(calls) < 3:
            raise _down()
        return "store"

    now = [0.0]
    assert open_store(DbSettings(), factory=factory, sleep=lambda s: now.__setitem__(0, now[0] + s), clock=lambda: now[0]) == "store"
    assert len(calls) == 3


def test_open_store_gives_up_after_the_wait():
    now = [0.0]

    def factory(db):
        raise _down()

    with pytest.raises(OperationalError):
        open_store(DbSettings(), wait_secs=10, factory=factory, sleep=lambda s: now.__setitem__(0, now[0] + s), clock=lambda: now[0])


def test_open_store_does_not_retry_other_errors():
    calls = []

    def factory(db):
        calls.append(1)
        raise ValueError("bad config")

    with pytest.raises(ValueError):
        open_store(DbSettings(), factory=factory, sleep=lambda s: None)
    assert len(calls) == 1


def test_shutdown_step_stops_waiting_for_a_dead_database():
    release = threading.Event()
    started = time.monotonic()
    assert _bounded(lambda: release.wait(5), "test step", secs=0.2) is False
    assert time.monotonic() - started < 2
    release.set()
    assert _bounded(lambda: None, "test step") is True
    assert _bounded(lambda: 1 / 0, "test step") is False
