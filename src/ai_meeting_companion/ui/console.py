from __future__ import annotations

import sys
import threading
from typing import TextIO

from ai_meeting_companion.core.agent import BaseAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.core.events import ERROR, LLM_RESPONSE, SCREEN_TEXT, STATUS, TRANSCRIPT, Event

_print_lock = threading.Lock()


class ConsolePrinter(BaseAgent):
    """Prints session activity to the terminal (the headless stand-in for the overlay)."""

    name = "console"
    kinds = frozenset({TRANSCRIPT, SCREEN_TEXT, LLM_RESPONSE, ERROR, STATUS})

    def __init__(self, bus: Bus, out: TextIO | None = None) -> None:
        super().__init__(bus)
        self._out = out or sys.stdout

    def handle(self, event: Event) -> None:
        if event.kind == TRANSCRIPT:
            line = f"[{event.payload.get('channel', 'audio')}] {event.text}"
        elif event.kind == SCREEN_TEXT:
            preview = event.text if len(event.text) <= 200 else event.text[:200] + "..."
            line = f"[screen] {preview}"
        elif event.kind == STATUS:
            line = f"[status] {event.text}"
        elif event.kind == LLM_RESPONSE:
            line = f"\n=== {event.payload.get('agent', event.source)} ===\n{event.text}\n"
        else:
            line = f"[error] {event.text}"
        with _print_lock:
            print(line, file=self._out, flush=True)
