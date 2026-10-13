from __future__ import annotations

import logging
import threading
from typing import ClassVar

from ai_meeting_companion.core.bus import Bus, Subscription
from ai_meeting_companion.core.events import ERROR, Event

log = logging.getLogger(__name__)

POLL_SECS = 0.2


class BaseAgent:
    """Runs on its own thread. Consumes subscribed events via ``handle`` and calls
    ``idle`` whenever no event arrived within the poll interval. Sensors that own a
    capture loop override ``run`` instead."""

    name: ClassVar[str] = "agent"
    kinds: ClassVar[frozenset[str]] = frozenset()
    stop_timeout: ClassVar[float] = 5.0  # how long stop() waits for the worker thread

    def __init__(self, bus: Bus) -> None:
        self.bus = bus
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._sub: Subscription | None = None

    # -- lifecycle -----------------------------------------------------
    def start(self) -> None:
        if self.kinds:
            self._sub = self.bus.subscribe(self.kinds)
        self._thread = threading.Thread(target=self._main, name=self.name, daemon=True)
        self._thread.start()

    def stop(self, timeout: float | None = None) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(self.stop_timeout if timeout is None else timeout)
        if self._sub is not None:
            self.bus.unsubscribe(self._sub)
        self.on_stop()

    @property
    def stopping(self) -> bool:
        return self._stop.is_set()

    # -- hooks ---------------------------------------------------------
    def on_stop(self) -> None:
        pass

    def handle(self, event: Event) -> None:
        pass

    def idle(self) -> None:
        pass

    def run(self) -> None:
        assert self._sub is not None, f"{self.name} has no subscription; override run()"
        while not self._stop.is_set():
            event = self._sub.get(timeout=POLL_SECS)
            if event is None:
                self._guarded(self.idle)
            else:
                self._guarded(self.handle, event)

    # -- helpers -------------------------------------------------------
    def publish(self, event: Event) -> None:
        self.bus.publish(event)

    def report_error(self, message: str) -> None:
        self.publish(Event(kind=ERROR, source=self.name, payload={"text": message, "agent": self.name}))

    def _guarded(self, fn, *args) -> None:
        try:
            fn(*args)
        except Exception as exc:  # an agent failure must not take the session down
            log.exception("%s failed", self.name)
            self.report_error(f"{type(exc).__name__}: {exc}")

    def _main(self) -> None:
        try:
            self.run()
        except Exception as exc:
            log.exception("%s crashed", self.name)
            self.report_error(f"{type(exc).__name__}: {exc}")
