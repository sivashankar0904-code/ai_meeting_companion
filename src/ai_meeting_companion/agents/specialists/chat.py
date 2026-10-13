from __future__ import annotations

from ai_meeting_companion.agents.specialists.base import SpecialistAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.core.events import USER_MESSAGE
from ai_meeting_companion.llm.chains import build_chain
from ai_meeting_companion.memory.session_memory import SessionMemory
from ai_meeting_companion.prompts.loader import build_system_prompt


class ChatAgent(SpecialistAgent):
    """Answers typed questions using the shared session timeline for context."""

    def __init__(
        self,
        bus: Bus,
        model,
        model_name: str,
        *,
        background: str = "",
        memory: SessionMemory | None = None,
        memory_chars: int = 8000,
    ) -> None:
        super().__init__(
            bus,
            name="chat",
            chain=build_chain(model, build_system_prompt("chat", background)),
            model_name=model_name,
            trigger_kind=USER_MESSAGE,
            memory=memory,
            memory_chars=memory_chars,
        )
