from __future__ import annotations

import queue
import threading
from typing import Callable, Iterable

from ai_meeting_companion.core.events import Event


class Subscription:
    """A private queue that receives every published event matching ``kinds``."""

    def __init__(self, kinds: Iterable[str] | None) -> None:
        self.kinds = frozenset(kinds) if kinds is not None else None
        self._queue: queue.Queue[Event] = queue.Queue()

    def matches(self, event: Event) -> bool:
        return self.kinds is None or event.kind in self.kinds

    def put(self, event: Event) -> None:
        self._queue.put(event)

    def get(self, timeout: float | None = None) -> Event | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None


class Bus:
    """Thread-safe publish/subscribe. Publishers never block on subscribers."""

    def __init__(self) -> None:
        self._subs: list[Subscription] = []
        self._taps: list[Callable[[Event], None]] = []
        self._lock = threading.Lock()

    def add_tap(self, tap: Callable[[Event], None]) -> None:
        """Call ``tap(event)`` synchronously on every publish, before subscribers see the event."""
        with self._lock:
            self._taps.append(tap)

    def subscribe(self, kinds: Iterable[str] | None = None) -> Subscription:
        sub = Subscription(kinds)
        with self._lock:
            self._subs.append(sub)
        return sub

    def unsubscribe(self, sub: Subscription) -> None:
        with self._lock:
            if sub in self._subs:
                self._subs.remove(sub)

    def publish(self, event: Event) -> None:
        with self._lock:
            subs = list(self._subs)
            taps = list(self._taps)
        for tap in taps:
            try:
                tap(event)
            except Exception:  # a broken tap must never stop the meeting
                pass
        for sub in subs:
            if sub.matches(event):
                sub.put(event)
