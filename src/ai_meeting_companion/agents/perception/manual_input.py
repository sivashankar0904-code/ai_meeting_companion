from __future__ import annotations

import sys
from typing import TextIO

from ai_meeting_companion.core.agent import BaseAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.core.events import SUGGEST_REQUEST, USER_MESSAGE, Event


class ManualInputAgent(BaseAgent):
    """Turns each line typed in the terminal into a user_message event; ``/suggest`` asks the Conversor."""

    name = "manual_input"
    stop_timeout = 0.0  # blocked in readline; the daemon thread is abandoned on exit

    def __init__(self, bus: Bus, stream: TextIO | None = None) -> None:
        super().__init__(bus)
        self._stream = stream or sys.stdin

    def run(self) -> None:
        # readline blocks and cannot be interrupted; the thread is a daemon so exit is not held up.
        while not self.stopping:
            line = self._stream.readline()
            if line == "":  # EOF
                return
            text = line.strip()
            if text.lower() == "/suggest":
                self.publish(Event(kind=SUGGEST_REQUEST, source=self.name, payload={"text": ""}))
            elif text:
                self.publish(Event(kind=USER_MESSAGE, source=self.name, payload={"text": text}))
