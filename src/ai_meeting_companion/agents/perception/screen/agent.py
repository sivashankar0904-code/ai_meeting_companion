from __future__ import annotations

import threading
from typing import Callable

from PIL import Image

from ai_meeting_companion.agents.perception.screen.hotkey import HotkeyListener
from ai_meeting_companion.agents.perception.screen.ocr import Ocr
from ai_meeting_companion.core.agent import POLL_SECS, BaseAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.core.events import SCREEN_TEXT, Event


class ScreenAgent(BaseAgent):
    """On hotkey: screenshot -> OCR -> screen_text event. Empty or unchanged text is skipped."""

    name = "screen"

    def __init__(
        self,
        bus: Bus,
        capture: Callable[[], Image.Image],
        ocr: Ocr,
        listener_factory: Callable[[Callable[[], None]], HotkeyListener] | None = None,
    ) -> None:
        super().__init__(bus)
        self._capture = capture
        self._ocr = ocr
        self._listener_factory = listener_factory
        self._listener: HotkeyListener | None = None
        self._requested = threading.Event()
        self._last_text = ""

    def trigger(self) -> None:
        """Request a capture (called from the hotkey thread)."""
        self._requested.set()

    def capture_once(self) -> Event | None:
        text = self._ocr(self._capture()).strip()
        if not text or text == self._last_text:
            return None
        self._last_text = text
        event = Event(kind=SCREEN_TEXT, source=self.name, payload={"text": text})
        self.publish(event)
        return event

    def run(self) -> None:
        if self._listener_factory is not None:
            self._listener = self._listener_factory(self.trigger)
            self._listener.start()
        while not self.stopping:
            if self._requested.wait(POLL_SECS):
                self._requested.clear()
                self._guarded(self.capture_once)

    def on_stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
