from __future__ import annotations

from ai_meeting_companion.agents.specialists.base import SpecialistAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.core.events import SCREEN_TEXT, Event
from ai_meeting_companion.llm.chains import build_chain
from ai_meeting_companion.memory.session_memory import SessionMemory
from ai_meeting_companion.prompts.loader import build_system_prompt


class ScreenAnalyzer(SpecialistAgent):
    def __init__(
        self, bus: Bus, model, model_name: str, *, memory: SessionMemory | None = None, memory_chars: int = 8000
    ) -> None:
        super().__init__(
            bus,
            name="screen_analyzer",
            chain=build_chain(model, build_system_prompt("screen_analyzer")),
            model_name=model_name,
            trigger_kind=SCREEN_TEXT,
            memory=memory,
            memory_chars=memory_chars,
        )

    def on_trigger(self, event: Event) -> None:
        self.ask(f"Text extracted from the screen:\n\n{event.text}", parent_id=event.id, exclude=[event.id])
