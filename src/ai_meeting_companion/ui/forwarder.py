from __future__ import annotations

from typing import Callable

from ai_meeting_companion.core.agent import BaseAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.core.events import ERROR, LLM_RESPONSE, SCREEN_TEXT, STATUS, TRANSCRIPT, USER_MESSAGE, Event


class BusForwarder(BaseAgent):
    """Hands every displayable event to a callback (the overlay's thread-safe Qt signal)."""

    name = "overlay_forwarder"
    kinds = frozenset({TRANSCRIPT, SCREEN_TEXT, USER_MESSAGE, LLM_RESPONSE, ERROR, STATUS})

    def __init__(self, bus: Bus, callback: Callable[[Event], None]) -> None:
        super().__init__(bus)
        self._callback = callback

    def handle(self, event: Event) -> None:
        self._callback(event)
