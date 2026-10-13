from __future__ import annotations

import time
from typing import Any, Iterable
from uuid import UUID

from langchain_core.runnables import Runnable

from ai_meeting_companion.core.agent import BaseAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.core.events import LLM_RESPONSE, Event
from ai_meeting_companion.memory.session_memory import SessionMemory


def content_text(content: Any) -> str:
    """AIMessage.content is a str or a list of content blocks; return the text."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type", "text") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


class SpecialistAgent(BaseAgent):
    """Consumes one trigger event kind, asks its chain, and publishes an llm_response.

    Every request carries the shared session timeline (``memory``), so all specialists work from
    the same picture of the meeting instead of each keeping a private history."""

    def __init__(
        self,
        bus: Bus,
        *,
        name: str,
        chain: Runnable,
        model_name: str,
        trigger_kind: str,
        memory: SessionMemory | None = None,
        memory_chars: int = 8000,
    ) -> None:
        super().__init__(bus)
        self.name = name
        self.chain = chain
        self.model_name = model_name
        self.trigger_kind = trigger_kind
        self.kinds = frozenset({trigger_kind})
        self.memory = memory
        self.memory_chars = memory_chars

    def handle(self, event: Event) -> None:
        if event.kind == self.trigger_kind:
            self.on_trigger(event)

    def on_trigger(self, event: Event) -> None:
        self.ask(event.text, parent_id=event.id, exclude=[event.id])

    def finalize(self, answer: str) -> tuple[str, dict[str, Any]] | None:
        """Turn the raw model reply into (text, extra payload), or None to publish nothing."""
        return answer, {}

    def build_input(self, text: str, exclude: Iterable[UUID] = ()) -> str:
        """The request text, preceded by the shared timeline (minus entries that are the request itself)."""
        context = ""
        if self.memory is not None and self.memory_chars > 0:
            context = self.memory.render(frozenset(exclude), self.memory_chars)
        if not context:
            return text
        return f"Session so far:\n{context}\n\n---\nNew request:\n{text}"

    def ask(
        self,
        text: str,
        parent_id: UUID | None = None,
        extra: dict[str, Any] | None = None,
        exclude: Iterable[UUID] = (),
    ) -> Event | None:
        started = time.perf_counter()
        message = self.chain.invoke({"history": [], "input": self.build_input(text, exclude)})
        latency_ms = int((time.perf_counter() - started) * 1000)
        final = self.finalize(content_text(message.content).strip())
        if final is None:
            return None
        answer, final_extra = final
        usage = getattr(message, "usage_metadata", None) or {}
        payload = {
            "text": answer,
            "agent": self.name,
            "model": self.model_name,
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "latency_ms": latency_ms,
            **final_extra,
            **(extra or {}),
        }
        response = Event(kind=LLM_RESPONSE, source=self.name, payload=payload, parent_id=parent_id)
        self.publish(response)
        return response
